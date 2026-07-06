"""bias_scoring 的输出结构（模块内部结果对象，非对外 API schema）。"""

from pydantic import BaseModel, Field

from app.services.bias_scoring.labels import BiasCategory


class OptionBiasResult(BaseModel):
    """单个选项的偏差计算结果。

    对被排除的无效选项或「不适用偏差」事件下的选项，偏差链路字段（``p`` … ``bias``）
    均为 ``None``，仅透传标识与原始价格。
    """

    option_id: str
    label: str | None = None
    price: float | None = None  # 原始价格透传

    excluded: bool = Field(default=False, description="是否为无效选项被排除")
    exclusion_reason: str | None = None

    p: float | None = Field(default=None, description="概率份额 p_i")
    trade: float | None = Field(default=None, description="交易热度 trade_i")
    social: float | None = Field(
        default=None, description="参与热度 social_i（退化时为 None）"
    )
    h: float | None = Field(default=None, description="热度合成分 h_i")
    hs: float | None = Field(default=None, description="热度份额 hs_i")
    d: float | None = Field(default=None, description="偏差 d_i = hs_i - p_i")
    bias: int | None = Field(default=None, description="偏差评分 bias_i ∈ [-100, 100]")

    category: BiasCategory | None = None
    label_zh: str | None = None
    label_en: str | None = None


class EventBiasResult(BaseModel):
    """单个事件的偏差计算结果。"""

    event_id: str
    applicable: bool = Field(description="是否适用偏差分析")
    not_applicable_reason: str | None = Field(
        default=None,
        description="不适用原因（single_option / no_valid_price）",
    )
    degraded_trade_only: bool = Field(
        default=False,
        description="是否退化为纯交易热度（bias-algorithm §3.5）",
    )
    comment_count: int | None = None  # 事件级评论数透传
    options: list[OptionBiasResult] = Field(default_factory=list)


class RankedOption(BaseModel):
    """排行榜单项：保留事件归属以便回跳（bias-algorithm §5、design D7）。"""

    event_id: str
    option_id: str
    label: str | None = None
    bias: int
    category: BiasCategory
    label_zh: str
    label_en: str


class RankingResult(BaseModel):
    """多事件排行分档结果（三档互斥无交集，bias-algorithm §5）。"""

    bubble_risk: list[RankedOption] = Field(default_factory=list)
    value_opportunity: list[RankedOption] = Field(default_factory=list)
    fairly_priced: list[RankedOption] = Field(default_factory=list)
