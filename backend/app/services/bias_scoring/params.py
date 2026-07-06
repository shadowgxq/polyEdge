"""bias_scoring 的可配置参数（bias-algorithm §7、design D8）。

业务可调项集中为一个带默认值的参数对象；默认值即 bias-algorithm §7 默认。
归一函数 ``norm`` 为钉死的份额型口径，**不在**可配置集内（见 calculator.norm）。
"""

from pydantic import BaseModel, Field

# 权重默认值：L0 交易关注度以近期成交为主（bias-algorithm §3.2 / §7）。
DEFAULT_ALPHA = 0.7
DEFAULT_BETA = 0.3
DEFAULT_VOL_WEIGHT = 0.0  # 累计成交量易污染实时热度，默认不参与 attention
DEFAULT_LIQ_WEIGHT = 0.10
DEFAULT_24H_WEIGHT = 0.45
DEFAULT_1WK_WEIGHT = 0.25
DEFAULT_TURN_WEIGHT = 0.20
DEFAULT_DEPTH_WEIGHT = 0.0  # MVP 不启用订单簿深度
DEFAULT_THRESHOLD = 15  # 三分类阈值 T

# ---- 多信号扩展默认值（bias-multi-signal，bias-algorithm §7 业务可调） ----
DEFAULT_FAVORITE_RANK_MAX = 3  # 身份池：排名 ≤ 此值入热门池
DEFAULT_FAVORITE_PROB_MIN = 0.20  # 身份池：概率份额 ≥ 此值入热门池
DEFAULT_LONGSHOT_PROB_MAX = 0.08  # 身份池：概率份额 < 此值且非热门入冷门池
DEFAULT_ATTENTION_EXPECTATION_GAMMA = 0.65  # 预期热度压缩指数：normalize(p^γ)
DEFAULT_MOMENTUM_REF = 0.10  # 动量归一参考（单日 10% 视为满标度）
DEFAULT_SPREAD_REF = 0.05  # 脆弱度归一参考（相对价差 5% 视为满标度）
DEFAULT_CROWD_REF = 0.20  # 拥挤度归一参考（crowding 0.20 视为满标度）
DEFAULT_OVERHEAT_HI = 60  # 过热分阈值：≥ 判过热
DEFAULT_WATCH_HI = 55  # 观察分阈值：≥ 判观察冷门
# 过热分权重（拥挤 / 动量 / 脆弱 / 加速），合计 1。
DEFAULT_OVERHEAT_W = (0.40, 0.30, 0.15, 0.15)
# 观察分权重（流动性健康 / 正动量 / 低脆弱 / 有成交），合计 1。
DEFAULT_WATCH_W = (0.40, 0.20, 0.30, 0.10)


class BiasParams(BaseModel):
    """偏差计算参数（默认值锚定 bias-algorithm §7）。"""

    model_config = {"frozen": True}

    alpha: float = Field(default=DEFAULT_ALPHA, description="交易热度权重 α")
    beta: float = Field(default=DEFAULT_BETA, description="参与热度权重 β")
    w_vol: float = Field(default=DEFAULT_VOL_WEIGHT, description="累计成交量份额权重")
    w_liq: float = Field(default=DEFAULT_LIQ_WEIGHT, description="流动性份额权重")
    w_24h: float = Field(default=DEFAULT_24H_WEIGHT, description="24h 成交量份额权重")
    w_1wk: float = Field(default=DEFAULT_1WK_WEIGHT, description="1w 成交量份额权重")
    w_turn: float = Field(default=DEFAULT_TURN_WEIGHT, description="换手率份额权重")
    w_depth: float = Field(
        default=DEFAULT_DEPTH_WEIGHT, description="订单簿深度份额权重（默认 0）"
    )
    threshold_t: int = Field(
        default=DEFAULT_THRESHOLD, description="三分类 / 排行分档阈值 T"
    )

    # ---- 多信号扩展参数（bias-multi-signal） ----
    favorite_rank_max: int = Field(
        default=DEFAULT_FAVORITE_RANK_MAX, description="热门池排名上限"
    )
    favorite_prob_min: float = Field(
        default=DEFAULT_FAVORITE_PROB_MIN, description="热门池概率份额下限"
    )
    longshot_prob_max: float = Field(
        default=DEFAULT_LONGSHOT_PROB_MAX, description="冷门池概率份额上限"
    )
    attention_expectation_gamma: float = Field(
        default=DEFAULT_ATTENTION_EXPECTATION_GAMMA,
        description="预期热度压缩指数（ExpectedAttention=normalize(p^γ)）",
    )
    momentum_ref: float = Field(
        default=DEFAULT_MOMENTUM_REF, description="动量归一参考"
    )
    spread_ref: float = Field(default=DEFAULT_SPREAD_REF, description="脆弱度归一参考")
    crowd_ref: float = Field(default=DEFAULT_CROWD_REF, description="拥挤度归一参考")
    overheat_hi: int = Field(default=DEFAULT_OVERHEAT_HI, description="过热分判定阈值")
    watch_hi: int = Field(default=DEFAULT_WATCH_HI, description="观察分判定阈值")
    overheat_weights: tuple[float, float, float, float] = Field(
        default=DEFAULT_OVERHEAT_W, description="过热分权重（拥挤/动量/脆弱/加速）"
    )
    watch_weights: tuple[float, float, float, float] = Field(
        default=DEFAULT_WATCH_W, description="观察分权重（流动性/动量/低脆弱/有成交）"
    )


DEFAULT_PARAMS = BiasParams()
