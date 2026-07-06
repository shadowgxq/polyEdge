"""市场快照持久化仓储（market-data-snapshot）。

只做 DB 读写、无业务规则（layer-definition.md）：把归一后的 `MarketEvent` 落库为最新
快照、按 slug / name 读回并重建领域对象。写入为 upsert（按唯一键覆盖），一次列表摄取
的「列表行 + 各事件行」在同一事务内提交（原子，避免半写）。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.session import transaction
from app.models.market_snapshot import MarketEventSnapshot, MarketListSnapshot
from app.schemas.market_data import MarketEvent


class MarketSnapshotRepository:
    """事件 / 列表最新快照的 DB 读写。"""

    def __init__(self, db: Session):
        self.db = db

    # ---------------- 读 ----------------

    def get_event(self, slug: str) -> MarketEvent | None:
        row = (
            self.db.query(MarketEventSnapshot)
            .filter(MarketEventSnapshot.slug == slug)
            .one_or_none()
        )
        if row is None:
            return None
        return MarketEvent.model_validate(row.payload)

    def get_list(self, name: str) -> list[MarketEvent] | None:
        """读列表快照：取有序 slug 集合 → 批量取事件快照 → 按原序返回；无列表行返回 None。"""
        list_row = (
            self.db.query(MarketListSnapshot)
            .filter(MarketListSnapshot.name == name)
            .one_or_none()
        )
        if list_row is None:
            return None
        slugs = list(list_row.slugs or [])
        if not slugs:
            return []
        rows = (
            self.db.query(MarketEventSnapshot)
            .filter(MarketEventSnapshot.slug.in_(slugs))
            .all()
        )
        event_by_slug = {
            row.slug: MarketEvent.model_validate(row.payload) for row in rows
        }
        # 按列表原序返回，跳过尚未落库的 slug（保持列表口径一致，不臆造）。
        return [event_by_slug[slug] for slug in slugs if slug in event_by_slug]

    # ---------------- 写（upsert） ----------------

    def save_list_snapshot(
        self, name: str, events: list[MarketEvent], fetched_at: datetime
    ) -> None:
        """摄取写入：upsert 各事件快照 + upsert 列表有序 slug 集合，同一事务提交。"""
        with transaction(self.db):
            for event in events:
                self._upsert_event(event, fetched_at)
            self._upsert_list(name, [event.slug for event in events], fetched_at)

    def save_event_snapshot(self, event: MarketEvent, fetched_at: datetime) -> None:
        """摄取写入：upsert 单事件快照；用于用户粘贴任意 slug 后的按需持久化。"""
        with transaction(self.db):
            self._upsert_event(event, fetched_at)

    def _upsert_event(self, event: MarketEvent, fetched_at: datetime) -> None:
        payload = event.model_dump(mode="json")
        row = (
            self.db.query(MarketEventSnapshot)
            .filter(MarketEventSnapshot.slug == event.slug)
            .one_or_none()
        )
        if row is None:
            self.db.add(
                MarketEventSnapshot(
                    slug=event.slug,
                    category=event.category,
                    payload=payload,
                    data_snapshot_at=event.data_snapshot_at,
                    fetched_at=fetched_at,
                )
            )
        else:
            row.category = event.category
            row.payload = payload
            row.data_snapshot_at = event.data_snapshot_at
            row.fetched_at = fetched_at

    def _upsert_list(self, name: str, slugs: list[str], fetched_at: datetime) -> None:
        row = (
            self.db.query(MarketListSnapshot)
            .filter(MarketListSnapshot.name == name)
            .one_or_none()
        )
        if row is None:
            self.db.add(
                MarketListSnapshot(name=name, slugs=slugs, fetched_at=fetched_at)
            )
        else:
            row.slugs = slugs
            row.fetched_at = fetched_at
