"""偏差计算主链路（bias-algorithm §3–§6、design D3–D6）。

纯函数、无副作用：输入已归一化的事件 → 输出每个选项的 bias_i 与三分类标签。
不依赖 repositories / DB / Redis / 网络，便于黄金 fixture 独立单测。
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.services.bias_scoring.contracts import EventInput, OptionInput
from app.services.bias_scoring.labels import (
    Pool,
    classify_option,
    label_en,
    label_zh,
)
from app.services.bias_scoring.params import DEFAULT_PARAMS, BiasParams
from app.services.bias_scoring.results import EventBiasResult, OptionBiasResult

# 不适用偏差分析的原因 key（design D6）。
REASON_SINGLE_OPTION = "single_option"
REASON_NO_VALID_PRICE = "no_valid_price"
# 无效选项排除原因（design D6）。
EXCLUSION_INVALID_PRICE = "invalid_price"

_BIAS_MIN = -100
_BIAS_MAX = 100

# 数值兜底极小量，避免除零（bias-multi-signal）。
_EPS = 1e-9


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
    """交易关注度 trade_i：近期成交优先的 L0 份额合成（+可选 depth，bias-algorithm §3.2）。"""
    vol_share = norm([_num(o.volume) for o in options])
    liq_share = norm([_num(o.liquidity) for o in options])
    v24_share = norm([_num(o.volume24hr) for o in options])
    v1wk_share = norm([_num(o.volume1wk) for o in options])
    turn_share = norm([_turnover(o) for o in options])

    trade = [
        params.w_vol * vol_share[i]
        + params.w_liq * liq_share[i]
        + params.w_24h * v24_share[i]
        + params.w_1wk * v1wk_share[i]
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


# ---------------- 多信号（bias-multi-signal，纯函数、缺失→0 兜底） ----------------


def _pool(rank: int, p_share: float, params: BiasParams) -> Pool:
    """身份池：由市场概率份额与排名决定，不由热度决定（design D3）。"""
    if rank <= params.favorite_rank_max or p_share >= params.favorite_prob_min:
        return Pool.FAVORITE
    if p_share < params.longshot_prob_max:
        return Pool.LONGSHOT
    return Pool.CONTENDER


def _expected_attention_shares(
    p_shares: Sequence[float], params: BiasParams
) -> list[float]:
    """非线性预期热度：normalize(p_i^γ)，避免热门被线性预期过度惩罚。"""
    gamma = max(params.attention_expectation_gamma, _EPS)
    expected = [p**gamma for p in p_shares]
    return norm(expected)


def _momentum(option: OptionInput, params: BiasParams) -> float:
    """价格动量：单日价格变化按参考归一到 [-1, 1]，缺失记 0。"""
    change = option.one_day_price_change
    if change is None:
        return 0.0
    return clamp(change / params.momentum_ref, -1.0, 1.0)


def _fragility(option: OptionInput, params: BiasParams) -> float:
    """流动性脆弱度：相对买卖价差按参考归一到 [0, 1]，缺失记 0（视为不脆弱/未知）。"""
    spread = option.spread
    price = option.price
    if spread is None or price is None or price <= 0:
        return 0.0
    return clamp((spread / price) / params.spread_ref, 0.0, 1.0)


def _acceleration(option: OptionInput) -> float:
    """成交加速：24h 成交量相对周均的偏离，归一到 [-1, 1]，缺失记 0。"""
    v24 = option.volume24hr
    v1wk = option.volume1wk
    if v24 is None or v1wk is None or v1wk <= 0:
        return 0.0
    daily_avg = v1wk / 7.0
    return clamp(v24 / (daily_avg + _EPS) - 1.0, -1.0, 1.0)


def _overheat_score(
    crowding: float,
    momentum: float,
    fragility: float,
    acceleration: float,
    params: BiasParams,
) -> float:
    """过热分 ∈ [0,100]：拥挤↑ + 动量↑ + 脆弱↑ + 加速↑ 的加权合成（design D5）。"""
    w = params.overheat_weights
    raw = (
        w[0] * clamp(crowding / params.crowd_ref, 0.0, 1.0)
        + w[1] * max(momentum, 0.0)
        + w[2] * fragility
        + w[3] * max(acceleration, 0.0)
    )
    return 100.0 * clamp(raw, 0.0, 1.0)


def _watch_score(
    liquidity_health: float,
    momentum: float,
    fragility: float,
    has_volume: float,
    params: BiasParams,
) -> float:
    """观察分 ∈ [0,100]：健康流动性 + 正动量 + 低脆弱 + 有成交（design D5，仅冷门池）。"""
    w = params.watch_weights
    raw = (
        w[0] * liquidity_health
        + w[1] * max(momentum, 0.0)
        + w[2] * (1.0 - fragility)
        + w[3] * has_volume
    )
    return 100.0 * clamp(raw, 0.0, 1.0)


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

    # 多信号预备份额（bias-multi-signal）：排名、流动性与非线性预期关注度。
    ranks = [1 + sum(1 for q in p_shares if q > p_shares[i]) for i in range(n)]
    liq_shares = norm([_num(o.liquidity) for o in valid])
    expected_attention_shares = _expected_attention_shares(p_shares, params)

    # §3.7 偏差、多信号与诚实标签。
    valid_results: list[OptionBiasResult] = []
    for i, option in enumerate(valid):
        d = hs_shares[i] - p_shares[i]
        attention_residual = hs_shares[i] - expected_attention_shares[i]
        bias = int(clamp(round_half_away_from_zero(d * 100), _BIAS_MIN, _BIAS_MAX))

        pool = _pool(ranks[i], p_shares[i], params)
        momentum = _momentum(option, params)
        fragility = _fragility(option, params)
        acceleration = _acceleration(option)
        overheat = _overheat_score(
            attention_residual, momentum, fragility, acceleration, params
        )

        if pool is Pool.LONGSHOT:
            liquidity_health = clamp(
                0.5 * (1.0 - fragility) + 0.5 * min(liq_shares[i] * n, 1.0), 0.0, 1.0
            )
            has_volume = (
                1.0 if (_num(option.volume) > 0 or _num(option.volume24hr) > 0) else 0.0
            )
            watch: float | None = _watch_score(
                liquidity_health, momentum, fragility, has_volume, params
            )
        else:
            watch = None

        category = classify_option(
            pool,
            attention_residual,
            overheat,
            watch or 0.0,
            params.threshold_t,
            overheat_hi=params.overheat_hi,
            watch_hi=params.watch_hi,
        )
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
                pool=pool,
                momentum=momentum,
                fragility=fragility,
                overheat_score=overheat,
                watch_score=watch,
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
