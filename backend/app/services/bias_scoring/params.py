"""bias_scoring 的可配置参数（bias-algorithm §7、design D8）。

业务可调项集中为一个带默认值的参数对象；默认值即 bias-algorithm §7 默认。
归一函数 ``norm`` 为钉死的份额型口径，**不在**可配置集内（见 calculator.norm）。
"""

from pydantic import BaseModel, Field

# 权重默认值：四项交易分量等权（bias-algorithm §3.2 / §7）。
DEFAULT_ALPHA = 0.7
DEFAULT_BETA = 0.3
DEFAULT_TRADE_WEIGHT = 0.25  # w_vol = w_liq = w_24h = w_turn = 1/4
DEFAULT_DEPTH_WEIGHT = 0.0  # MVP 不启用订单簿深度
DEFAULT_THRESHOLD = 15  # 三分类阈值 T


class BiasParams(BaseModel):
    """偏差计算参数（默认值锚定 bias-algorithm §7）。"""

    model_config = {"frozen": True}

    alpha: float = Field(default=DEFAULT_ALPHA, description="交易热度权重 α")
    beta: float = Field(default=DEFAULT_BETA, description="参与热度权重 β")
    w_vol: float = Field(default=DEFAULT_TRADE_WEIGHT, description="成交量份额权重")
    w_liq: float = Field(default=DEFAULT_TRADE_WEIGHT, description="流动性份额权重")
    w_24h: float = Field(default=DEFAULT_TRADE_WEIGHT, description="24h 成交量份额权重")
    w_turn: float = Field(default=DEFAULT_TRADE_WEIGHT, description="换手率份额权重")
    w_depth: float = Field(
        default=DEFAULT_DEPTH_WEIGHT, description="订单簿深度份额权重（默认 0）"
    )
    threshold_t: int = Field(
        default=DEFAULT_THRESHOLD, description="三分类 / 排行分档阈值 T"
    )


DEFAULT_PARAMS = BiasParams()
