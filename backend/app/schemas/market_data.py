"""归一化事件/选项数据契约（market-data-model）。

跨 change 共享的内部市场数据模型，供 `bias-algorithm` 与 `analysis-api` 复用：
字段口径映射（价格主源/回退、成交量/流动性/24h/参与人数/评论数）、数据快照时间、
二元 vs 多 outcome 粒度处理、无 per-option 参与数据判定谓词。
口径对齐 data-source §2、bias-algorithm §2/§3。
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PriceSource(str, Enum):
    """选项价格实际来源标注（data-source §2、bias-algorithm §3.1）。"""

    CLOB_MIDPOINT = "clob_midpoint"  # 主源：CLOB midpoint / best bid-ask
    OUTCOME_PRICES_FALLBACK = "outcome_prices_fallback"  # 退化回退：Gamma outcomePrices
    UNAVAILABLE = "unavailable"  # 两源均不可得，price 缺失


class MarketOption(BaseModel):
    """归一化选项级数据。

    量纲字段（volume/liquidity/volume24hr/traders）不可得时置 None，
    诚实标缺失（degraded_note），不臆造/估算，交由下游按缺失兜底。
    """

    outcome: str  # 选项标识（如 "Yes" / "Argentina"），用于区分同一事件下多选项
    icon_url: str | None = None  # Polymarket 选项图标/图片 URL，仅作展示元数据
    price: float | None = None  # 隐含概率 0~1，主源 CLOB、退化回退 outcomePrices
    price_source: PriceSource = PriceSource.UNAVAILABLE
    volume: float | None = None
    liquidity: float | None = None
    volume24hr: float | None = None
    traders: int | None = None  # per-option 参与/持仓人数，可空
    degraded_note: str | None = None  # 口径限制说明（如多 outcome 无法拆到选项级）

    # 零新请求白拿的扩展信号字段（同 Gamma /events 响应，bias-multi-signal）。
    # 缺失置 None，诚实标缺失，交由下游按缺失兜底（多 outcome 无法拆到选项级时同 volume 置 None）。
    one_day_price_change: float | None = None  # 单日价格变化，动量信号源
    one_week_price_change: float | None = None  # 单周价格变化
    best_bid: float | None = None  # 盘口买一
    best_ask: float | None = None  # 盘口卖一
    spread: float | None = None  # 买卖价差（上游已算），流动性脆弱度源
    volume1wk: float | None = None  # 近一周成交量，成交加速源
    volume1mo: float | None = None  # 近一月成交量
    competitive: float | None = None  # Polymarket 竞争度指标


class MarketEvent(BaseModel):
    """归一化事件级数据，承载选项集合与事件级关注度字段。"""

    slug: str
    title: str
    category: str | None = None
    comment_count: int | None = None  # 事件级 commentCount，不下放到单选项
    options: list[MarketOption] = Field(default_factory=list)
    data_snapshot_at: datetime  # 数据快照获取时刻（data-source §4、PRD §5.3）


def has_participation(option: MarketOption) -> bool:
    """「无 per-option 参与数据」判定谓词（PRD §5.2、bias-algorithm §3.5）。

    - `traders` 缺失或为 `null` → False（无参与数据，供下游触发全事件退化）
    - 值为 `0` → True（有效 0，正常参与，不触发退化）
    """
    return option.traders is not None
