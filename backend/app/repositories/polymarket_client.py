"""Polymarket 只读客户端（polymarket-client）。

对接 Gamma API（事件/市场元数据）与 CLOB API（选项价格），将拉取结果归一到
`market-data-model` 契约（`MarketEvent` / `MarketOption`）。仅只读请求，不触达任何
交易 / 下单 / 钱包 endpoint（PRD §1.3、data-source §5）。

上游 429 / 瞬时错误采用指数退避重试，耗尽后抛 `UpstreamFetchError`（技术层错误），
由 `services` 的降级链转缓存回退 / `UpstreamUnavailableException`（data-source §5）。

字段真实可得性（traders/holders、多 outcome 粒度、CLOB midpoint）待探针验证，映射
集中在此处便于后续固化（design Risks）。
"""

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.schemas.market_data import MarketEvent, MarketOption, PriceSource

logger = logging.getLogger(__name__)

# 触发退避重试的 HTTP 状态码：限流 + 服务端瞬时错误。
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class UpstreamFetchError(Exception):
    """上游拉取失败（退避重试耗尽或不可重试错误）。技术层异常，由 service 降级处理。"""


def _loads_list(value: object) -> list:
    """Gamma 常把数组字段序列化为 JSON 字符串，这里统一解析为 list。"""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _to_float(value: object) -> float | None:
    """安全转 float：None / 空串 / 非数值 → None（缺失，不臆造）。"""
    if value is None or value == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    """安全转 int：None / 空 / 非数值 → None。值为 0 保留为有效 0。"""
    if value is None or value == "":
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _market_signals(market: dict) -> dict[str, float | None]:
    """从 market 级 Gamma 字段抽取零新请求白拿的扩展信号（bias-multi-signal）。

    全部经 ``_to_float`` 缺失兜底为 None；键名与 ``MarketOption`` 扩展字段对齐，
    供 ``**`` 展开到构造调用（多 outcome 无法拆到选项级时由调用方传空 dict）。
    """
    return {
        "one_day_price_change": _to_float(market.get("oneDayPriceChange")),
        "one_week_price_change": _to_float(market.get("oneWeekPriceChange")),
        "best_bid": _to_float(market.get("bestBid")),
        "best_ask": _to_float(market.get("bestAsk")),
        "spread": _to_float(market.get("spread")),
        "volume1wk": _to_float(market.get("volume1wk")),
        "volume1mo": _to_float(market.get("volume1mo")),
        "competitive": _to_float(market.get("competitive")),
    }


class PolymarketClient:
    """Gamma + CLOB 双 API 只读客户端。"""

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        gamma_base_url: str | None = None,
        clob_base_url: str | None = None,
        retry_base_delay_seconds: float | None = None,
        retry_max_attempts: int | None = None,
        retry_max_delay_seconds: float | None = None,
        detail_use_midpoint: bool | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._gamma_base_url = (
            gamma_base_url or settings.polymarket_gamma_base_url
        ).rstrip("/")
        self._clob_base_url = (
            clob_base_url or settings.polymarket_clob_base_url
        ).rstrip("/")
        self._retry_base_delay = (
            retry_base_delay_seconds
            if retry_base_delay_seconds is not None
            else settings.market_retry_base_delay_seconds
        )
        self._retry_max_attempts = (
            retry_max_attempts
            if retry_max_attempts is not None
            else settings.market_retry_max_attempts
        )
        self._retry_max_delay = (
            retry_max_delay_seconds
            if retry_max_delay_seconds is not None
            else settings.market_retry_max_delay_seconds
        )
        # 详情路径是否取 CLOB midpoint；默认随配置（请求路径默认关，见 config）。
        self._detail_use_midpoint = (
            detail_use_midpoint
            if detail_use_midpoint is not None
            else settings.market_detail_use_midpoint
        )
        self._sleep = sleep
        self._client = http_client or httpx.Client(
            timeout=settings.polymarket_request_timeout_seconds
        )

    # ---------------- 只读 HTTP + 退避重试 ----------------

    def _request(self, base_url: str, path: str, params: dict | None = None) -> object:
        """只读 GET，带指数退避重试；耗尽后抛 UpstreamFetchError（不静默返回空）。"""
        url = f"{base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt >= self._retry_max_attempts:
                    raise UpstreamFetchError(
                        f"transport error after {attempt} attempts: {exc}"
                    ) from exc
                self._backoff(attempt)
                continue

            if response.status_code in _RETRYABLE_STATUS:
                if attempt >= self._retry_max_attempts:
                    raise UpstreamFetchError(
                        f"status {response.status_code} after {attempt} attempts"
                    )
                self._backoff(attempt)
                continue

            if response.status_code >= 400:
                # 不可重试的客户端错误（如 404），直接上抛失败，不重试。
                raise UpstreamFetchError(f"status {response.status_code} for {url}")

            try:
                return response.json()
            except json.JSONDecodeError as exc:
                raise UpstreamFetchError(f"invalid json from {url}: {exc}") from exc

    def _backoff(self, attempt: int) -> None:
        delay = min(
            self._retry_base_delay * (2 ** (attempt - 1)), self._retry_max_delay
        )
        logger.warning(
            "polymarket upstream retry attempt=%s backoff=%.2fs", attempt, delay
        )
        self._sleep(delay)

    # ---------------- CLOB 价格（主源） ----------------

    def _fetch_midpoint(self, token_id: str | None) -> float | None:
        """取 CLOB midpoint 作主价源；不可得（含上游失败）时返回 None 以触发退化回退。"""
        if not token_id:
            return None
        try:
            payload = self._request(
                self._clob_base_url, "/midpoint", params={"token_id": token_id}
            )
        except UpstreamFetchError:
            return None
        if isinstance(payload, dict):
            return _to_float(payload.get("mid"))
        return None

    # ---------------- 归一映射 ----------------

    def _normalize_event(
        self, raw: dict, snapshot_at: datetime, *, use_midpoint: bool
    ) -> MarketEvent:
        options: list[MarketOption] = []
        for market in raw.get("markets") or []:
            options.extend(self._normalize_market(market, use_midpoint=use_midpoint))
        return MarketEvent(
            slug=str(raw.get("slug") or ""),
            title=str(raw.get("title") or raw.get("slug") or ""),
            category=raw.get("category"),
            comment_count=_to_int(raw.get("commentCount")),
            options=options,
            data_snapshot_at=snapshot_at,
        )

    def _normalize_market(
        self, market: dict, *, use_midpoint: bool
    ) -> list[MarketOption]:
        outcomes = _loads_list(market.get("outcomes"))
        prices = _loads_list(market.get("outcomePrices"))
        token_ids = _loads_list(market.get("clobTokenIds"))
        market_volume = _to_float(market.get("volume"))
        market_liquidity = _to_float(market.get("liquidity"))
        market_volume24hr = _to_float(market.get("volume24hr"))
        # 扩展信号为 market 级白拿字段；与 volume 同处理：可拆到选项时映射，多 outcome 置 None。
        market_signals = _market_signals(market)
        group_title = str(market.get("groupItemTitle") or "").strip()

        # 分组式二元子市场（如「某队夺冠 Yes/No」，60 支队 = 60 个此类市场）：
        # 折叠为「一个候选项」= 组标题（球队/候选人名），概率取 Yes 侧，market 级量纲直接
        # 作该候选项级（对齐 Polymarket 原生「每队一行」交互，且避免拍平成匿名 Yes/No、
        # 避免 Yes/No 各领一份 volume 的重复计数）。
        if group_title and _is_yes_no(outcomes):
            token_id = token_ids[0] if token_ids else None
            price, source = self._resolve_price(
                token_id, prices, 0, use_midpoint=use_midpoint
            )
            return [
                MarketOption(
                    outcome=group_title,
                    price=price,
                    price_source=source,
                    volume=market_volume,
                    liquidity=market_liquidity,
                    volume24hr=market_volume24hr,
                    traders=_to_int(market.get("numTraders")),
                    degraded_note=None,
                    **market_signals,
                )
            ]

        # 二元市场（market ≈ 单选项）字段直接作选项级；多 outcome 单市场无法拆到
        # 选项级时该分量置缺失并标注，不臆造/估算（data-source §2、design D3）。
        is_binary = len(outcomes) == 2

        options: list[MarketOption] = []
        for index, label in enumerate(outcomes):
            token_id = token_ids[index] if index < len(token_ids) else None
            price, source = self._resolve_price(
                token_id, prices, index, use_midpoint=use_midpoint
            )
            if is_binary:
                volume, liquidity, volume24hr, note = (
                    market_volume,
                    market_liquidity,
                    market_volume24hr,
                    None,
                )
                signals = market_signals
            else:
                volume = liquidity = volume24hr = None
                note = "multi-outcome market: per-option volume/liquidity unavailable"
                signals = {}
            options.append(
                MarketOption(
                    outcome=str(label),
                    price=price,
                    price_source=source,
                    volume=volume,
                    liquidity=liquidity,
                    volume24hr=volume24hr,
                    traders=_to_int(market.get("numTraders")),
                    degraded_note=note,
                    **signals,
                )
            )
        return options

    def _resolve_price(
        self, token_id: str | None, prices: list, index: int, *, use_midpoint: bool
    ) -> tuple[float | None, PriceSource]:
        """解析选项价格并标注实际价源。

        列表路径（use_midpoint=False）不逐 outcome 外呼 CLOB，直接用 Gamma 内联
        outcomePrices，避免 N+1 串行拉取拖垮首屏（design D8 首屏可用优先）；单事件
        详情路径（use_midpoint=True）主取更新鲜的 CLOB midpoint，不可得再回退
        outcomePrices，仍不可得记为缺失（不臆造）。
        """
        if use_midpoint:
            midpoint = self._fetch_midpoint(token_id)
            if midpoint is not None:
                return midpoint, PriceSource.CLOB_MIDPOINT
        if index < len(prices):
            fallback = _to_float(prices[index])
            if fallback is not None:
                return fallback, PriceSource.OUTCOME_PRICES_FALLBACK
        return None, PriceSource.UNAVAILABLE

    # ---------------- 对外拉取 ----------------

    def fetch_event_by_slug(self, slug: str) -> MarketEvent:
        """按 slug 从 Gamma 拉事件元数据 + 价格，归一为内部事件模型。

        请求路径默认不逐 outcome 取 CLOB midpoint（`market_detail_use_midpoint`，默认关闭），
        只做 1 次 Gamma 拉取用内联 outcomePrices，避免多市场事件 midpoint 扇出拖到超时；
        更新鲜的 midpoint 由后台摄取离线补齐。
        """
        snapshot_at = datetime.now(timezone.utc)
        payload = self._request(self._gamma_base_url, "/events", params={"slug": slug})
        raw = self._first_event(payload)
        if raw is None:
            raise UpstreamFetchError(f"event not found for slug={slug}")
        return self._normalize_event(
            raw, snapshot_at, use_midpoint=self._detail_use_midpoint
        )

    def fetch_popular_events(self, limit: int | None = None) -> list[MarketEvent]:
        """按热门规则（成交量降序）拉取默认列表，数量不超过配置的批量上限。

        列表路径：仅 1 次 Gamma 拉取，价格用内联 outcomePrices，不逐 outcome 外呼
        CLOB（避免整页 N+1 串行拉取拖垮首屏；更新鲜的 midpoint 留给详情页）。
        """
        batch_limit = limit or settings.market_prefetch_batch_limit
        snapshot_at = datetime.now(timezone.utc)
        payload = self._request(
            self._gamma_base_url,
            "/events",
            params={
                "order": "volume",
                "ascending": "false",
                "active": "true",
                "closed": "false",
                "limit": batch_limit,
            },
        )
        events = payload if isinstance(payload, list) else []
        return [
            self._normalize_event(raw, snapshot_at, use_midpoint=False)
            for raw in events[:batch_limit]
        ]

    def fetch_world_cup_events(self, limit: int | None = None) -> list[MarketEvent]:
        """按 FIFA 世界杯 tag 服务端拉取默认子集（等价 /sports/world-cup 页面口径）。

        用 `tag_slug` 让 Gamma 服务端按世界杯 tag 聚合并按成交量降序返回，避免此前
        「拉任意 active 再过滤」几乎命中不到世界杯事件的问题；`_matches_world_cup`
        作服务端结果的防御性二次收敛（不引入第三方源，仅筛选）。
        """
        batch_limit = limit or settings.market_prefetch_batch_limit
        snapshot_at = datetime.now(timezone.utc)
        payload = self._request(
            self._gamma_base_url,
            "/events",
            params={
                "tag_slug": settings.world_cup_tag_slug,
                "order": "volume",
                "ascending": "false",
                "active": "true",
                "closed": "false",
                "limit": batch_limit,
            },
        )
        events = payload if isinstance(payload, list) else []
        matched = [raw for raw in events if _matches_world_cup(raw)]
        return [
            self._normalize_event(raw, snapshot_at, use_midpoint=False)
            for raw in matched[:batch_limit]
        ]

    @staticmethod
    def _first_event(payload: object) -> dict | None:
        if isinstance(payload, list):
            return payload[0] if payload else None
        if isinstance(payload, dict):
            return payload
        return None


def _is_yes_no(outcomes: list) -> bool:
    """判定是否为标准二元 Yes/No 选项集（大小写与前后空白不敏感）。"""
    if len(outcomes) != 2:
        return False
    normalized = [str(o).strip().lower() for o in outcomes]
    return normalized == ["yes", "no"]


def _matches_world_cup(raw: dict) -> bool:
    """按配置标签/关键词判定事件是否属于世界杯子集。"""
    tags = raw.get("tags") or []
    tag_texts = {
        str(tag.get("slug") or tag.get("label") or "").lower()
        for tag in tags
        if isinstance(tag, dict)
    }
    if tag_texts & set(settings.world_cup_tag_list):
        return True
    haystack = f"{raw.get('title', '')} {raw.get('slug', '')}".lower()
    return any(keyword in haystack for keyword in settings.world_cup_keyword_list)
