"""bias_scoring 的输出结构（模块内部结果对象，非对外 API schema）。"""

from pydantic import BaseModel, Field

from app.services.bias_scoring.labels import BiasCategory, Pool


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

    # —— 多信号扩展（bias-multi-signal，可空，透传缺失） ——
    pool: Pool | None = Field(default=None, description="身份池：热门/中位/冷门")
    momentum: float | None = Field(default=None, description="价格动量信号 ∈ [-1,1]")
    fragility: float | None = Field(default=None, description="流动性脆弱度 ∈ [0,1]")
    overheat_score: float | None = Field(default=None, description="过热分 ∈ [0,100]")
    watch_score: float | None = Field(
        default=None, description="观察分 ∈ [0,100]（仅冷门池）"
    )

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
    # 多信号扩展（bias-multi-signal，可空；用于三榜诚实重定义的排序与透传）。
    pool: Pool | None = None
    momentum: float | None = None
    fragility: float | None = None
    overheat_score: float | None = None
    watch_score: float | None = None


class RankingResult(BaseModel):
    """多事件排行分档结果（bias-multi-signal 诚实三榜，互斥无交集）。

    字段名保留兼容既有装配，语义诚实重定义：
    - ``bubble_risk``：过热榜（过热热门 + 过热中位 + 被炒作冷门）
    - ``value_opportunity``：观察榜（观察冷门 + 低关注热门）
    - ``fairly_priced``：合理（共识热门 + 中位竞争者 + 普通冷门）
    """

    bubble_risk: list[RankedOption] = Field(default_factory=list)
    value_opportunity: list[RankedOption] = Field(default_factory=list)
    fairly_priced: list[RankedOption] = Field(default_factory=list)
