"""偏差计算主链路（bias-algorithm §3–§6、design D3–D6）。

纯函数、无副作用：输入已归一化的事件 → 输出每个选项的 bias_i 与三分类标签。
不依赖 repositories / DB / Redis / 网络，便于黄金 fixture 独立单测。
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.services.bias_scoring.contracts import EventInput, OptionInput
from app.services.bias_scoring.labels import classify, label_en, label_zh
from app.services.bias_scoring.params import DEFAULT_PARAMS, BiasParams
from app.services.bias_scoring.results import EventBiasResult, OptionBiasResult

# 不适用偏差分析的原因 key（design D6）。
REASON_SINGLE_OPTION = "single_option"
REASON_NO_VALID_PRICE = "no_valid_price"
# 无效选项排除原因（design D6）。
EXCLUSION_INVALID_PRICE = "invalid_price"

_BIAS_MIN = -100
_BIAS_MAX = 100


def _num(value: float | None) -> float:
    """缺失（None）按 0 处理，用于交易分量的除零兜底（bias-algorithm §3.2）。"""
    return float(value) if value is not None else 0.0


def clamp(value: float, low: float, high: float) -> float:
    """将 value 截断到 [low, high]。"""
    return max(low, min(high, value))


def norm(values: Sequence[float]) -> list[float]:
    """份额型归一 norm(x_i)=x_i/Σ_j x_j（钉死，非可配置，bias-algorithm §3.2 / design D3）。

    分量全 0 或 Σ=0 时该分量对所有选项记 0，不产生 NaN。
    """
    total = 0.0
    for value in values:
        total += value
    if total <= 0:
        return [0.0 for _ in values]
    return [value / total for value in values]


def round_half_away_from_zero(value: float) -> int:
    """半值向上进位（round half away from zero，bias-algorithm §3.7 / design D5）。

    ``14.5 → 15``、``-14.5 → -15``；用 Decimal ROUND_HALF_UP（Python 语义即远离零方向），
    避免内建 round 的 banker's rounding 在 .5 边界抖动。
    """
    quantized = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(quantized)


def _turnover(option: OptionInput) -> float:
    """换手率 turnover_i = clamp(volume24hr/volume, 0, 1)；volume=0 记 0（bias-algorithm §3.2）。"""
    volume = _num(option.volume)
    if volume <= 0:
        return 0.0
    return clamp(_num(option.volume24hr) / volume, 0.0, 1.0)


def _trade_shares(options: Sequence[OptionInput], params: BiasParams) -> list[float]:
    """交易热度 trade_i：四项份额归一后加权合成（+可选 depth，bias-algorithm §3.2）。"""
    vol_share = norm([_num(o.volume) for o in options])
    liq_share = norm([_num(o.liquidity) for o in options])
    v24_share = norm([_num(o.volume24hr) for o in options])
    turn_share = norm([_turnover(o) for o in options])

    trade = [
        params.w_vol * vol_share[i]
        + params.w_liq * liq_share[i]
        + params.w_24h * v24_share[i]
        + params.w_turn * turn_share[i]
        for i in range(len(options))
    ]

    if params.w_depth > 0:
        depth_share = norm([_num(o.depth) for o in options])
        trade = [
            trade[i] + params.w_depth * depth_share[i] for i in range(len(options))
        ]

    return trade


def _is_valid_option(option: OptionInput) -> bool:
    """有效选项：价格存在且 > 0（价格全 0 / 缺失视为无效，bias-algorithm §6 / design D6）。"""
    return option.price is not None and option.price > 0


def _passthrough_result(
    option: OptionInput,
    *,
    excluded: bool,
    exclusion_reason: str | None = None,
) -> OptionBiasResult:
    """无 bias 的透传结果（不适用事件下的选项 / 被排除的无效选项）。"""
    return OptionBiasResult(
        option_id=option.option_id,
        label=option.label,
        price=option.price,
        excluded=excluded,
        exclusion_reason=exclusion_reason,
    )


def compute_event_bias(
    event: EventInput,
    params: BiasParams = DEFAULT_PARAMS,
) -> EventBiasResult:
    """计算单个事件内所有选项的偏差与三分类（bias-algorithm §3–§6）。

    步骤严格按 §3 顺序：排除无效选项 → 适用性判定 → p_i → trade_i → 退化判定 →
    social_i → h_i → hs_i → d_i → bias_i → 三分类。
    """
    valid = [o for o in event.options if _is_valid_option(o)]

    # 适用性边界（design D6）：有效选项 < 2 → 不适用，仅透传，不产 bias_i。
    if len(valid) < 2:
        reason = REASON_SINGLE_OPTION if len(valid) == 1 else REASON_NO_VALID_PRICE
        return EventBiasResult(
            event_id=event.event_id,
            applicable=False,
            not_applicable_reason=reason,
            degraded_trade_only=False,
            comment_count=event.comment_count,
            options=[
                _passthrough_result(
                    o,
                    excluded=not _is_valid_option(o),
                    exclusion_reason=None
                    if _is_valid_option(o)
                    else EXCLUSION_INVALID_PRICE,
                )
                for o in event.options
            ],
        )

    n = len(valid)

    # §3.1 概率份额 p_i（在剩余有效选项集上归一，Σ p_i = 1）。
    p_shares = norm([_num(o.price) for o in valid])

    # §3.2 交易热度 trade_i。
    trade = _trade_shares(valid, params)

    # §3.3 / §3.5 参与数据退化：任一有效选项 traders 缺失(None) → 全事件退化（0 为有效值）。
    degraded = any(o.traders is None for o in valid)

    if degraded:
        social: list[float | None] = [None] * n
        heat = list(trade)  # h_i = trade_i（等价 β=0）
    else:
        social_shares = norm([_num(o.traders) for o in valid])
        social = list(social_shares)
        heat = [
            params.alpha * trade[i] + params.beta * social_shares[i] for i in range(n)
        ]

    # §3.6 热度份额 hs_i；Σ h_j = 0 → 均分 1/n。
    total_h = sum(heat)
    if total_h <= 0:
        hs_shares = [1.0 / n for _ in range(n)]
    else:
        hs_shares = [h / total_h for h in heat]

    # §3.7 偏差与偏差评分。
    valid_results: list[OptionBiasResult] = []
    for i, option in enumerate(valid):
        d = hs_shares[i] - p_shares[i]
        bias = int(clamp(round_half_away_from_zero(d * 100), _BIAS_MIN, _BIAS_MAX))
        category = classify(bias, params.threshold_t)
        valid_results.append(
            OptionBiasResult(
                option_id=option.option_id,
                label=option.label,
                price=option.price,
                excluded=False,
                p=p_shares[i],
                trade=trade[i],
                social=social[i],
                h=heat[i],
                hs=hs_shares[i],
                d=d,
                bias=bias,
                category=category,
                label_zh=label_zh(category),
                label_en=label_en(category),
            )
        )

    # 按原始选项顺序装配：有效选项取计算结果，无效选项透传标注排除。
    result_by_id = {r.option_id: r for r in valid_results}
    options_out = [
        result_by_id[o.option_id]
        if o.option_id in result_by_id
        else _passthrough_result(
            o, excluded=True, exclusion_reason=EXCLUSION_INVALID_PRICE
        )
        for o in event.options
    ]

    return EventBiasResult(
        event_id=event.event_id,
        applicable=True,
        not_applicable_reason=None,
        degraded_trade_only=degraded,
        comment_count=event.comment_count,
        options=options_out,
    )
