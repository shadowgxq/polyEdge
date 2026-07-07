"""分析结果对外组合编排（analysis-api、design D2–D9）。

只做编排：调用 `poly-data-integration` 的 `MarketDataService` 缓存读取 →
`bias-scoring` 纯函数计算偏差/三分类/排行 → 装配对外 `schemas/analysis` 出参。
不重复实现数据接入（属 poly-data-integration）或偏差公式（属 bias-algorithm），
依赖只向下 `services →（poly service / bias 纯函数）`。数据边界作为成功响应内标注，
上游 `UpstreamUnavailableException` 不吞交全局 handler，回退快照透传 data_snapshot_at。
"""

import re
from collections.abc import Callable, Sequence
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import EventNotFoundException, UpstreamUnavailableException
from app.schemas.analysis import (
    BiasLabel,
    EventCard,
    EventCategory,
    EventDetail,
    EventListResponse,
    EventSearchResult,
    OptionAnalysis,
    OptionOverview,
    RankingBoards,
    RankingItem,
    SearchCandidate,
    SearchScope,
)
from app.schemas.market_data import MarketEvent
from app.services.bias_scoring import (
    EventInput,
    OptionInput,
    compute_event_bias,
    rank_options,
)
from app.services.bias_scoring.results import EventBiasResult, OptionBiasResult
from app.services.market_data_service import (
    MarketDataService,
    build_market_data_service,
)

# 从 Polymarket 事件链接路径提取 slug：/event/<slug>[/...]。
_EVENT_SLUG_PATH = re.compile(r"/event/([^/?#]+)")
# 合法 slug 字符集（url-safe），用于裸 slug 输入的有效性判定。
_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9._~-]+$")

# 上游名称搜索：(query, limit) -> 匹配事件列表。当前上游搜索能力待探针固化
# （design Open Questions），未注入时走本地缓存模糊回退。
UpstreamSearch = Callable[[str, int], list[MarketEvent]]


class AnalysisService:
    """组合数据 service 与偏差算法，产出对外分析结果。"""

    def __init__(
        self,
        market_data: MarketDataService,
        upstream_search: UpstreamSearch | None = None,
    ):
        self._market_data = market_data
        self._upstream_search = upstream_search

    # ---------------- D3：数据 → 算法输入适配（集中一处） ----------------

    @staticmethod
    def _to_event_input(event: MarketEvent) -> EventInput:
        """`MarketEvent`/`MarketOption` → `bias-scoring` 输入契约；字段仅在此对齐。"""
        return EventInput(
            event_id=event.slug,
            comment_count=event.comment_count,
            options=[
                OptionInput(
                    option_id=option.outcome,
                    label=option.outcome,
                    price=option.price,
                    volume=option.volume,
                    liquidity=option.liquidity,
                    volume24hr=option.volume24hr,
                    traders=option.traders,
                    one_day_price_change=option.one_day_price_change,
                    spread=option.spread,
                    volume1wk=option.volume1wk,
                )
                for option in event.options
            ],
        )

    @staticmethod
    def _to_label(result: OptionBiasResult) -> BiasLabel | None:
        if result.label_zh is None or result.label_en is None:
            return None
        return BiasLabel(zh=result.label_zh, en=result.label_en)

    # ---------------- 单事件明细（D2/D7/D9） ----------------

    def get_event_detail(
        self, slug: str, *, force_refresh: bool = False
    ) -> EventDetail:
        """按 slug 读取 → 适配 → 计算 → 装配明细（含退化/排除/不适用标注）。"""
        event = self._market_data.get_event(slug, force_refresh=force_refresh)
        return self._build_event_detail(event)

    def _build_event_detail(self, event: MarketEvent) -> EventDetail:
        result = compute_event_bias(self._to_event_input(event))
        icon_by_outcome = {option.outcome: option.icon_url for option in event.options}
        return EventDetail(
            slug=event.slug,
            title=event.title,
            comment_count=result.comment_count,
            applicable=result.applicable,
            degraded_trade_only=result.degraded_trade_only,
            data_snapshot_at=event.data_snapshot_at,
            options=[
                OptionAnalysis(
                    name=option.label or option.option_id,
                    icon_url=icon_by_outcome.get(option.option_id),
                    price=option.price,
                    heat=option.hs,
                    bias_score=option.bias,
                    label=self._to_label(option),
                    excluded=option.excluded,
                    pool=option.pool.value if option.pool is not None else None,
                    momentum=option.momentum,
                    fragility=option.fragility,
                    overheat_score=option.overheat_score,
                    watch_score=option.watch_score,
                )
                for option in result.options
            ],
        )

    # ---------------- 默认列表（D4） ----------------

    def get_event_list(
        self, category: EventCategory, page: int, page_size: int
    ) -> EventListResponse:
        """按分类读取默认列表 → 逐事件算偏差 → 装配卡片（概览标签取 |bias| 最大选项）。"""
        events = self._read_category_events(category)
        page_size = min(page_size, settings.event_list_page_size)
        start = (page - 1) * page_size
        page_events = events[start : start + page_size]
        items = [self._build_event_card(event) for event in page_events]
        return EventListResponse(
            category=category,
            items=items,
            total_count=len(events),
            has_more=len(events) > start + page_size,
        )

    def _build_event_card(self, event: MarketEvent) -> EventCard:
        result = compute_event_bias(self._to_event_input(event))
        overview = self._pick_overview_option(event, result)
        overview_label = self._to_label(overview) if overview is not None else None
        overview_name = (
            (overview.label or overview.option_id) if overview is not None else None
        )
        preview_options = self._preview_options(event.options)
        return EventCard(
            slug=event.slug,
            title=event.title,
            options=[
                OptionOverview(
                    name=option.outcome,
                    icon_url=option.icon_url,
                    price=option.price,
                )
                for option in preview_options
            ],
            options_total=len(event.options),
            overview_label=overview_label,
            overview_option_name=overview_name,
            applicable=result.applicable,
            data_snapshot_at=event.data_snapshot_at,
        )

    @staticmethod
    def _preview_options(options: Sequence) -> list:
        """卡片选项预览：按隐含概率降序（缺价排末尾）取 TopN，多候选事件只露头部。"""
        ordered = sorted(
            options,
            key=lambda option: (option.price is not None, option.price or 0.0),
            reverse=True,
        )
        return ordered[: settings.event_card_option_preview]

    @staticmethod
    def _pick_overview_option(
        event: MarketEvent, result: EventBiasResult
    ) -> OptionBiasResult | None:
        """取事件内 |bias| 最大选项作卡片概览标签；不适用事件返回 None（D4）。

        确定性 tie-break（|bias| 并列）：先较大 volume，再原始选项顺序，避免展示抖动。
        """
        if not result.applicable:
            return None
        volume_by_outcome = {o.outcome: (o.volume or 0.0) for o in event.options}
        candidates = [
            (index, option)
            for index, option in enumerate(result.options)
            if option.bias is not None and not option.excluded
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda pair: (
                abs(pair[1].bias),
                volume_by_outcome.get(pair[1].option_id, 0.0),
                -pair[0],
            ),
        )[1]

    # ---------------- 多事件排行（D5） ----------------

    def get_rankings(self, category: EventCategory, top_n: int) -> RankingBoards:
        """按分类读取默认列表所有事件 → 算法分档三榜 → 每榜 TopN 截取 + 事件归属。"""
        events = self._read_category_events(category)
        title_by_slug = {event.slug: event.title for event in events}
        price_by_key = {
            (event.slug, option.outcome): option.price
            for event in events
            for option in event.options
        }
        ranking = rank_options([self._to_event_input(event) for event in events])

        def to_items(ranked: Sequence) -> list[RankingItem]:
            return [
                RankingItem(
                    event_slug=item.event_id,
                    event_title=title_by_slug.get(item.event_id, item.event_id),
                    option_name=item.label or item.option_id,
                    price=price_by_key.get((item.event_id, item.option_id)),
                    bias_score=item.bias,
                    label=BiasLabel(zh=item.label_zh, en=item.label_en),
                    pool=item.pool.value if item.pool is not None else None,
                    momentum=item.momentum,
                    fragility=item.fragility,
                    overheat_score=item.overheat_score,
                    watch_score=item.watch_score,
                )
                for item in ranked[:top_n]
            ]

        return RankingBoards(
            category=category,
            bubble=to_items(ranking.bubble_risk),
            underhyped=to_items(ranking.value_opportunity),
            fair=to_items(ranking.fairly_priced),
        )

    # ---------------- 事件输入：slug 解析 + 名称搜索（D8） ----------------

    def resolve_event(self, raw_input: str) -> EventDetail:
        """从链接/slug 提取 slug → 判定有效性 → 按 slug 拉取明细；解析不出抛「未找到」。

        缓存优先（不强制回源）：命中直接返回，未命中按需单次拉取，避免请求线程被上游拖慢。
        """
        slug = self._extract_slug(raw_input)
        if slug is None:
            raise EventNotFoundException()
        return self.get_event_detail(slug)

    @staticmethod
    def _extract_slug(raw_input: str) -> str | None:
        """从 Polymarket 事件链接或裸 slug 提取并校验 slug；无效返回 None。"""
        value = (raw_input or "").strip()
        if not value:
            return None
        if "://" in value or value.startswith("/") or "/event/" in value:
            parsed = urlparse(value if "://" in value else f"//{value}", scheme="")
            match = _EVENT_SLUG_PATH.search(parsed.path)
            slug = match.group(1) if match else ""
        else:
            slug = value
        slug = slug.strip()
        if not slug or not _SLUG_PATTERN.match(slug):
            return None
        return slug

    def search_events(self, query: str, limit: int | None = None) -> EventSearchResult:
        """名称搜索：优先上游搜索，不可用则已缓存事件集本地模糊匹配并标搜索范围。"""
        limit = limit or settings.event_search_limit
        term = (query or "").strip()
        if not term:
            return EventSearchResult(
                candidates=[], search_scope=SearchScope.LOCAL_CACHE
            )

        if self._upstream_search is not None:
            try:
                matched = self._upstream_search(term, limit)
            except Exception:  # noqa: BLE001 - 上游搜索不可用即退化本地，不阻断
                matched = None
            if matched is not None:
                return EventSearchResult(
                    candidates=self._to_candidates(matched[:limit]),
                    search_scope=SearchScope.UPSTREAM,
                )

        cached = self._local_cached_events()
        needle = term.lower()
        matched = [
            event
            for event in cached
            if needle in event.title.lower() or needle in event.slug.lower()
        ]
        return EventSearchResult(
            candidates=self._to_candidates(matched[:limit]),
            search_scope=SearchScope.LOCAL_CACHE,
        )

    @staticmethod
    def _to_candidates(events: Sequence[MarketEvent]) -> list[SearchCandidate]:
        return [SearchCandidate(slug=event.slug, title=event.title) for event in events]

    def _local_cached_events(self) -> list[MarketEvent]:
        """汇总已缓存的默认事件集（热门 + 世界杯）供本地模糊回退；上游不可用则跳过。"""
        events: list[MarketEvent] = []
        seen: set[str] = set()
        for reader in (
            self._market_data.get_popular_events,
            self._market_data.get_world_cup_events,
        ):
            try:
                fetched = reader()
            except UpstreamUnavailableException:
                continue
            for event in fetched:
                if event.slug not in seen:
                    seen.add(event.slug)
                    events.append(event)
        return events

    # ---------------- 分类读取 ----------------

    def _read_category_events(self, category: EventCategory) -> list[MarketEvent]:
        if category is EventCategory.WORLD_CUP:
            return self._market_data.get_world_cup_events()
        return self._market_data.get_popular_events()


def build_analysis_service(db: Session | None = None) -> AnalysisService:
    """装配分析组合 service（复用市场数据 service 工厂）。

    注入 db 会话时市场数据 service 启用 DB 快照层；请求路径经 `Depends(get_db)` 传入。
    """
    return AnalysisService(build_market_data_service(db))
