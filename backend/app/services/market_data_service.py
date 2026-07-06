"""市场数据业务编排（services）。

编排 client 拉取 → 归一 → 写缓存 → 返回带快照时间的领域值；降级/退避编排只在 service
（依赖只向下 `services → repositories`）。降级链（design D8）：

    命中 fresh 缓存直接返回
      → 未命中回源拉取（client 内含指数退避重试）
        → 拉取成功写缓存并返回
        → 拉取失败（退避耗尽）优先回退 fallback 缓存快照（带其 data_snapshot_at）
          → 无缓存则抛 UpstreamUnavailableException（由 analysis-api 全局 handler 转错误态），
            不静默失败。
"""

import logging
from collections.abc import Callable

from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableException
from app.repositories.market_data_cache_repository import MarketDataCacheRepository
from app.repositories.polymarket_client import PolymarketClient, UpstreamFetchError
from app.repositories.polymarket_mock import MockPolymarketClient
from app.schemas.market_data import MarketEvent

logger = logging.getLogger(__name__)

_POPULAR_LIST = "popular"
_WORLD_CUP_LIST = "world_cup"

# client 只需满足这三个拉取方法（PolymarketClient / MockPolymarketClient 皆可）。
MarketDataClient = PolymarketClient | MockPolymarketClient


def build_polymarket_client() -> MarketDataClient:
    """按配置装配真实或 Mock 客户端；Mock 仅在开关开启时进入，不入生产数据路径。"""
    if settings.polymarket_mock_enabled:
        return MockPolymarketClient(fault_mode=settings.polymarket_fault_mode)
    return PolymarketClient()


class MarketDataService:
    """市场数据编排：拉取归一 + 分层缓存 + 降级回退。"""

    def __init__(
        self,
        client: MarketDataClient,
        cache: MarketDataCacheRepository,
    ):
        self._client = client
        self._cache = cache

    def get_event(self, slug: str, *, force_refresh: bool = False) -> MarketEvent:
        """按 slug 取单事件：fresh 缓存优先，回源失败回退 fallback，无缓存报错。"""
        if not force_refresh:
            cached = self._cache.get_fresh_event(slug)
            if cached is not None:
                return cached
        try:
            event = self._client.fetch_event_by_slug(slug)
        except UpstreamFetchError as exc:
            fallback = self._cache.get_fallback_event(slug)
            if fallback is not None:
                logger.warning(
                    "upstream fetch failed, serving stale snapshot slug=%s: %s",
                    slug,
                    exc,
                )
                return fallback
            raise UpstreamUnavailableException() from exc
        self._cache.set_event(event)
        return event

    def get_popular_events(
        self, limit: int | None = None, *, force_refresh: bool = False
    ) -> list[MarketEvent]:
        """取热门默认列表（成交量等排序），受批量上限约束。"""
        return self._get_list(
            _POPULAR_LIST,
            lambda: self._client.fetch_popular_events(limit),
            force_refresh=force_refresh,
        )

    def get_world_cup_events(
        self, limit: int | None = None, *, force_refresh: bool = False
    ) -> list[MarketEvent]:
        """取世界杯默认子集（按标签/关键词筛选同一数据源）。"""
        return self._get_list(
            _WORLD_CUP_LIST,
            lambda: self._client.fetch_world_cup_events(limit),
            force_refresh=force_refresh,
        )

    def prefetch_default_lists(self) -> None:
        """定时预取：强制回源热门 + 世界杯默认列表入缓存；单项失败记录日志、走降级、不中断。"""
        for name, fetch in (
            (_POPULAR_LIST, self.get_popular_events),
            (_WORLD_CUP_LIST, self.get_world_cup_events),
        ):
            try:
                events = fetch(settings.market_prefetch_batch_limit, force_refresh=True)
                logger.info("prefetched list=%s count=%s", name, len(events))
            except UpstreamUnavailableException:
                logger.warning("prefetch list=%s skipped: upstream unavailable", name)
            except Exception:  # noqa: BLE001 - 预取不得中断调度进程
                logger.exception("prefetch list=%s failed unexpectedly", name)

    def _get_list(
        self,
        name: str,
        fetch: Callable[[], list[MarketEvent]],
        *,
        force_refresh: bool,
    ) -> list[MarketEvent]:
        if not force_refresh:
            cached = self._cache.get_fresh_list(name)
            if cached is not None:
                return cached
        try:
            events = fetch()
        except UpstreamFetchError as exc:
            fallback = self._cache.get_fallback_list(name)
            if fallback is not None:
                logger.warning(
                    "upstream fetch failed, serving stale list=%s: %s", name, exc
                )
                return fallback
            raise UpstreamUnavailableException() from exc
        self._cache.set_list(name, events)
        return events


def build_market_data_service() -> MarketDataService:
    """装配一个市场数据 service（供路由依赖 / 定时预取复用）。"""
    return MarketDataService(build_polymarket_client(), MarketDataCacheRepository())
