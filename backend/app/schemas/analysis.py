"""分析结果对外响应契约（analysis-api）。

组合 `market-data-model`（归一化数据）与 `bias-scoring`（偏差/三分类/排行）产出，
装配成对外 API 出参模型（snake_case Pydantic v2），一律经 `ApiResponse[T]` 返回。
口径锚定 PRD §4.1/§4.3/§4.4、bias-algorithm §3/§4/§5、design D3–D9。
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """默认列表 / 排行的事件分类（PRD §4.1）。"""

    HOT = "hot"
    WORLD_CUP = "world_cup"


class SearchScope(str, Enum):
    """名称搜索的实际搜索范围（design D8、data-source §3）。"""

    UPSTREAM = "upstream"  # Polymarket 搜索
    LOCAL_CACHE = "local_cache"  # 已缓存事件集本地模糊匹配


class BiasLabel(BaseModel):
    """三分类标签的中 / 英两套文案，供前端按语言渲染（bias-algorithm §4）。"""

    zh: str
    en: str


class OptionOverview(BaseModel):
    """事件卡片上的选项赔率概览（PRD §4.1）。"""

    name: str
    price: float | None = None


class OptionAnalysis(BaseModel):
    """单选项分析结果（PRD §4.3、bias-algorithm §3/§4）。

    被排除的无效选项或不适用偏差事件下的选项：偏差字段为 None，仅透传原始价格。
    """

    name: str  # 选项名（outcome）
    price: float | None = None  # 赔率 / 隐含概率
    heat: float | None = None  # 热度份额 hs_i（退化/排除时可空）
    bias_score: int | None = None  # 偏差评分 bias_i ∈ [-100, 100]（= 交易集中度残差）
    label: BiasLabel | None = None  # 诚实标签（zh/en，八类之一），无偏差时为 None
    excluded: bool = False  # 是否为无效选项被排除

    # 多信号扩展（bias-multi-signal，可空，向后兼容）。
    pool: str | None = None  # 身份池：favorite / contender / longshot
    momentum: float | None = None  # 价格动量 ∈ [-1,1]
    fragility: float | None = None  # 流动性脆弱度 ∈ [0,1]
    overheat_score: float | None = None  # 过热分 ∈ [0,100]
    watch_score: float | None = None  # 观察分 ∈ [0,100]（仅冷门池）


class EventDetail(BaseModel):
    """单事件明细（PRD §4.3、design D2/D7/D9）。"""

    slug: str
    title: str
    comment_count: int | None = None  # 事件级评论数，不参与单选项偏差
    applicable: bool  # 是否适用偏差分析
    degraded_trade_only: bool = False  # 是否退化为纯交易热度
    data_snapshot_at: datetime  # 数据快照时间（透传，可能为回退快照）
    options: list[OptionAnalysis] = Field(default_factory=list)


class EventCard(BaseModel):
    """默认列表事件卡片（PRD §4.1/AC-1、design D4）。"""

    slug: str
    title: str
    # 选项按隐含概率降序的 TopN 预览（多候选事件如世界杯冠军只展示前几名）。
    options: list[OptionOverview] = Field(default_factory=list)
    # 该事件选项总数，供前端在预览外提示「+N 更多」并引导进详情页。
    options_total: int = 0
    # 事件级概览偏差标签：取事件内 |bias| 最大选项的三分类标签；不适用时为 None。
    overview_label: BiasLabel | None = None
    overview_option_name: str | None = None  # 概览标签对应的选项名
    applicable: bool  # 是否适用偏差分析（不适用则前端展示「不适用」）
    data_snapshot_at: datetime


class EventListResponse(BaseModel):
    """默认列表出参（PRD §4.1）。"""

    category: EventCategory
    items: list[EventCard] = Field(default_factory=list)
    has_more: bool = False  # 是否还有下一页（空态时为 False）


class RankingItem(BaseModel):
    """榜单项：保留事件归属以便前端回跳（PRD §4.4、bias-algorithm §5）。"""

    event_slug: str
    event_title: str
    option_name: str
    price: float | None = None
    bias_score: int
    label: BiasLabel

    # 多信号扩展（bias-multi-signal，可空，向后兼容）。
    pool: str | None = None
    momentum: float | None = None
    fragility: float | None = None
    overheat_score: float | None = None
    watch_score: float | None = None


class RankingBoards(BaseModel):
    """多事件排行三榜（互斥无交集，PRD §4.4、bias-algorithm §5）。"""

    category: EventCategory
    bubble: list[RankingItem] = Field(default_factory=list)  # 过热榜（兼容字段名）
    underhyped: list[RankingItem] = Field(default_factory=list)  # 观察榜（兼容字段名）
    fair: list[RankingItem] = Field(default_factory=list)  # 合理列表


class SearchCandidate(BaseModel):
    """名称搜索候选事件（PRD §4.2）。"""

    slug: str
    title: str


class EventSearchResult(BaseModel):
    """名称搜索结果（含搜索范围标注，design D8）。"""

    candidates: list[SearchCandidate] = Field(default_factory=list)
    search_scope: SearchScope


class ResolveEventRequest(BaseModel):
    """事件输入解析入参：Polymarket 事件链接或 slug（design D8）。"""

    input: str = Field(min_length=1, description="Polymarket 事件链接或 slug")
