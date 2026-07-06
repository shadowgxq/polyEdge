"""bias_scoring 模块的输入契约。

定义偏差计算所需的**模块内部输入数据结构**（非对外 API schema）。字段命名锚定
bias-algorithm §2 / data-source §2。

契约假设（design D2）：
- 选项级字段（``price`` / ``volume`` / ``liquidity`` / ``volume24hr`` / ``traders``
  / ``depth``）为上游 ``poly-data-integration`` 归一化后产物；本模块只消费、不负责
  拉取与字段归一。
- ``traders`` 的真实可得性由 ``poly-data-integration`` 的 API 探针固化；本模块只按
  「缺失 / ``None`` = 无参与数据（触发退化），``0`` = 有效 0（正常参与）」谓词处理
  （bias-algorithm §3.3 / §3.5），不假设该字段一定可得。
- 多 outcome market 的 ``volume`` / ``liquidity`` 若仅 market 级、无法拆到选项，
  上游以缺失（``None``）透传，本模块按份额型归一的除零兜底记 0（bias-algorithm §3.2）。
- 若上游归一化产物字段名与此处不一致，由集成时的适配层对齐，本模块计算口径不变。
"""

from pydantic import BaseModel, Field


class OptionInput(BaseModel):
    """单个选项的归一化输入（bias-algorithm §2）。"""

    option_id: str = Field(description="选项唯一标识，用于回溯与榜单归属")
    label: str | None = Field(default=None, description="选项展示名（outcome），仅透传")
    price: float | None = Field(default=None, description="选项当前价格 / 隐含概率原值")
    volume: float | None = Field(default=None, description="累计成交量")
    liquidity: float | None = Field(default=None, description="流动性")
    volume24hr: float | None = Field(default=None, description="24h 成交量")
    traders: float | None = Field(
        default=None,
        description="per-option 参与 / 持仓人数（traders/holders 之一）；None=无、0=有效 0",
    )
    depth: float | None = Field(
        default=None, description="订单簿深度（可选，MVP 默认不参与）"
    )
    # 多信号扩展输入（bias-multi-signal，零新请求白拿；缺失→None，计算按 0 兜底）。
    one_day_price_change: float | None = Field(
        default=None, description="单日价格变化，动量信号源（bias-algorithm §3）"
    )
    spread: float | None = Field(
        default=None, description="买卖价差，流动性脆弱度信号源"
    )
    volume1wk: float | None = Field(
        default=None, description="近一周成交量，成交加速信号源"
    )


class EventInput(BaseModel):
    """单个事件的归一化输入（bias-algorithm §2）。"""

    event_id: str = Field(description="事件唯一标识")
    options: list[OptionInput] = Field(
        description="事件内选项集合（单/多 market 均已展平为选项）"
    )
    comment_count: int | None = Field(
        default=None,
        description="事件级评论数，仅透传作关注度标签，不参与单选项偏差（bias-algorithm §2）",
    )
