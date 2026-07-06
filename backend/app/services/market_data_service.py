"""市场数据业务编排（services）。

编排 client 拉取 → 归一 → 写缓存/快照 → 返回带快照时间的领域值；降级/退避编排只在
service（依赖只向下 `services → repositories`）。

数据分层：**上游（仅后台摄取触达）→ DB 快照（持久源）→ Redis（热缓存）→ serving**。
serving（请求路径）「只读」：Redis 命中直接返回，未命中读 DB 快照并回填 Redis，
**永不在请求线程同步回源列表**（上游慢/挂也不拖垮请求）；回源仅由后台摄取
（force_refresh=True）承担，成功后同时写 Redis + DB。重启后 Redis 冷、DB 仍在，
读 DB 即恢复，无冷启动空窗。

单事件 `get_event`：Redis → DB 快照 → 按需单次回源（用户粘贴的任意 slug 未预摄取时）。
DB 读写为「尽力而为」（DB 故障降级为不可用，不影响 Redis serving）。
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableException
from app.repositories.market_data_cache_repository import MarketDataCacheRepository
from app.repositories.market_snapshot_repository import MarketSnapshotRepository
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
    """市场数据编排：拉取归一 + DB 快照 + 分层缓存 + 降级回退。"""

    def __init__(
        self,
        client: MarketDataClient,
        cache: MarketDataCacheRepository,
        snapshots: MarketSnapshotRepository | None = None,
    ):
        self._client = client
        self._cache = cache
        # 无 snapshots（未注入 DB 会话）时退化为纯 Redis 行为，向后兼容既有装配/测试。
        self._snapshots = snapshots

    def get_event(self, slug: str, *, force_refresh: bool = False) -> MarketEvent:
        """按 slug 取单事件：Redis fresh → DB 快照 → 按需回源，回源失败回退 fallback。"""
        if not force_refresh:
            cached = self._cache.get_fresh_event(slug)
            if cached is not None:
                return cached
            db_event = self._read_db_event(slug)
            if db_event is not None:
                self._cache.set_event(db_event)  # 回填 Redis 热缓存
                return db_event
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
        self._cache.claim_refresh(f"event:{slug}")
        self._save_db_event(event)
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
        """定时预取：热门 + 世界杯默认列表入缓存；与请求触发刷新共享限频锁。"""
        for name in (_POPULAR_LIST, _WORLD_CUP_LIST):
            refreshed = self.maybe_refresh_list(name)
            if refreshed:
                logger.info("prefetch list=%s submitted", name)
            else:
                logger.info("prefetch list=%s skipped: refresh throttled", name)

    def maybe_refresh_event(self, slug: str) -> bool:
        """请求路径登记单事件刷新意图：同一 slug 限频，后台执行实际回源。"""
        if not self._cache.claim_refresh(f"event:{slug}"):
            return False
        try:
            self.get_event(slug, force_refresh=True)
        except UpstreamUnavailableException:
            logger.warning(
                "background refresh event skipped: upstream unavailable slug=%s", slug
            )
        except Exception:  # noqa: BLE001 - 后台刷新不得影响请求响应
            logger.exception("background refresh event failed slug=%s", slug)
        return True

    def maybe_refresh_list(self, name: str) -> bool:
        """请求路径登记列表刷新意图：同一列表限频，后台执行实际回源。"""
        if not self._cache.claim_refresh(f"list:{name}"):
            return False
        try:
            if name == _WORLD_CUP_LIST:
                self.get_world_cup_events(
                    settings.market_prefetch_batch_limit, force_refresh=True
                )
            elif name == _POPULAR_LIST:
                self.get_popular_events(
                    settings.market_prefetch_batch_limit, force_refresh=True
                )
            else:
                logger.warning("background refresh list skipped: unknown list=%s", name)
        except UpstreamUnavailableException:
            logger.warning(
                "background refresh list skipped: upstream unavailable list=%s", name
            )
        except Exception:  # noqa: BLE001 - 后台刷新不得影响请求响应
            logger.exception("background refresh list failed list=%s", name)
        return True

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
            # 请求路径「只读」：Redis 未命中读 DB 持久快照并回填 Redis，永不同步回源。
            db_list = self._read_db_list(name)
            if db_list is not None:
                self._cache.set_list(name, db_list)  # 回填 Redis（含逐事件回填）
                return db_list
            # DB 也无（尚未摄取）：退 Redis fallback 快照，再无则空，由后台摄取补齐。
            return self._cache.get_fallback_list(name) or []
        # 仅后台摄取（force_refresh=True）真正回源拉取并写 Redis + DB。
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
        self._save_db_list(name, events)
        return events

    # ---------------- DB 快照读写（尽力而为，故障降级不影响 Redis serving） ----------------

    def _read_db_event(self, slug: str) -> MarketEvent | None:
        if self._snapshots is None:
            return None
        try:
            return self._snapshots.get_event(slug)
        except SQLAlchemyError:
            logger.warning("db snapshot read failed slug=%s", slug, exc_info=True)
            return None

    def _read_db_list(self, name: str) -> list[MarketEvent] | None:
        if self._snapshots is None:
            return None
        try:
            return self._snapshots.get_list(name)
        except SQLAlchemyError:
            logger.warning("db snapshot read failed list=%s", name, exc_info=True)
            return None

    def _save_db_list(self, name: str, events: list[MarketEvent]) -> None:
        if self._snapshots is None:
            return
        try:
            self._snapshots.save_list_snapshot(name, events, datetime.now(timezone.utc))
        except SQLAlchemyError:
            logger.warning("db snapshot write failed list=%s", name, exc_info=True)

    def _save_db_event(self, event: MarketEvent) -> None:
        if self._snapshots is None:
            return
        try:
            self._snapshots.save_event_snapshot(event, datetime.now(timezone.utc))
        except SQLAlchemyError:
            logger.warning(
                "db snapshot write failed slug=%s", event.slug, exc_info=True
            )


def build_market_data_service(db: Session | None = None) -> MarketDataService:
    """装配市场数据 service：注入 db 会话时启用 DB 快照层（请求路径读、摄取写）。"""
    snapshots = MarketSnapshotRepository(db) if db is not None else None
    return MarketDataService(
        build_polymarket_client(), MarketDataCacheRepository(), snapshots
    )
