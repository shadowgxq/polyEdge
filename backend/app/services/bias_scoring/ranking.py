"""多事件排行分档口径（bias-algorithm §5、design D7）。

对一组事件的所有选项各自在其所属事件内算 bias_i，再按与三分类阈值 T 对齐、
互斥无交集的口径分三档。TopN 截取属对外接口层（analysis-api），本模块只给全量分档。
"""

from collections.abc import Sequence

from app.services.bias_scoring.calculator import compute_event_bias
from app.services.bias_scoring.contracts import EventInput
from app.services.bias_scoring.labels import BiasCategory
from app.services.bias_scoring.params import DEFAULT_PARAMS, BiasParams
from app.services.bias_scoring.results import RankedOption, RankingResult


def rank_options(
    events: Sequence[EventInput],
    params: BiasParams = DEFAULT_PARAMS,
) -> RankingResult:
    """对一组事件的所有有效选项分档（三档互斥无交集、无遗漏，bias-algorithm §5）。

    - 泡沫风险榜：``bias_i >= +T``，按 bias_i 降序
    - 冷门机会榜：``bias_i <= -T``，按 bias_i 升序
    - 合理列表：``|bias_i| < T``
    每项保留事件归属（event_id）以便回跳。不适用事件 / 被排除选项不入榜。
    """
    ranked: list[RankedOption] = []
    for event in events:
        event_result = compute_event_bias(event, params)
        if not event_result.applicable:
            continue
        for option in event_result.options:
            if option.excluded or option.bias is None or option.category is None:
                continue
            ranked.append(
                RankedOption(
                    event_id=event_result.event_id,
                    option_id=option.option_id,
                    label=option.label,
                    bias=option.bias,
                    category=option.category,
                    label_zh=option.label_zh or "",
                    label_en=option.label_en or "",
                )
            )

    bubble = [r for r in ranked if r.category == BiasCategory.BUBBLE_RISK]
    value = [r for r in ranked if r.category == BiasCategory.VALUE_OPPORTUNITY]
    fair = [r for r in ranked if r.category == BiasCategory.FAIRLY_PRICED]

    bubble.sort(key=lambda r: r.bias, reverse=True)
    value.sort(key=lambda r: r.bias)

    return RankingResult(
        bubble_risk=bubble,
        value_opportunity=value,
        fairly_priced=fair,
    )
