"""市场数据快照持久化模型（market-data-snapshot）。

后台摄取任务把归一后的事件/默认列表落库为「最新快照」，作为 serving 的持久数据源
（Redis 之下、上游之上）：重启不再冷启动雪崩，上游慢/挂时用户仍读到最近快照。
仅存最新一份（按 slug / name upsert）；历史趋势为后续扩展，另起表，不在此。

- `MarketEventSnapshot`：按 slug 存单事件最新归一快照（完整 `MarketEvent` 落 payload）。
- `MarketListSnapshot`：按 name（popular / world_cup）存默认列表的有序 slug 集合。
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class MarketEventSnapshot(Base):
    """单事件最新归一快照（按 slug 唯一，摄取时 upsert）。"""

    __tablename__ = "market_event_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    # 完整 MarketEvent 的 model_dump(mode="json")，读回时 model_validate 重建领域对象。
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    data_snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MarketListSnapshot(Base):
    """默认列表最新快照：有序 slug 集合（按 name 唯一，摄取时 upsert）。"""

    __tablename__ = "market_list_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # 有序 slug 数组（保留上游排序，如成交量降序），读回时按序取事件快照。
    slugs: Mapped[list] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
