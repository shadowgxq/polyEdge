"""多事件排行分档口径（bias-algorithm §5、bias-multi-signal design D7）。

对一组事件的所有选项各自在其所属事件内算多信号与诚实标签，再诚实重定义三榜：
- 过热榜（``bubble_risk`` 字段）：过热热门 + 过热中位 + 被炒作冷门，按过热分降序
- 观察榜（``value_opportunity`` 字段）：观察冷门 + 低关注热门，按观察分 / |bias| 降序
- 合理（``fairly_priced`` 字段）：共识热门 + 中位竞争者 + 普通冷门
TopN 截取属对外接口层（analysis-api），本模块只给全量分档。
"""

from collections.abc import Sequence

from app.services.bias_scoring.calculator import compute_event_bias
from app.services.bias_scoring.contracts import EventInput
from app.services.bias_scoring.labels import BiasCategory
from app.services.bias_scoring.params import DEFAULT_PARAMS, BiasParams
from app.services.bias_scoring.results import RankedOption, RankingResult

# 诚实三榜的标签归属（互斥无交集）。
_OVERHEATED = {
    BiasCategory.OVERHEATED_FAVORITE,
    BiasCategory.OVERHEATED_CONTENDER,
    BiasCategory.HYPED_LONGSHOT,
}
_WATCH = {
    BiasCategory.WATCH_LONGSHOT,
    BiasCategory.LOW_ATTENTION_FAVORITE,
}


def rank_options(
    events: Sequence[EventInput],
    params: BiasParams = DEFAULT_PARAMS,
) -> RankingResult:
    """对一组事件的所有有效选项诚实分三榜（互斥无交集、无遗漏，bias-multi-signal）。

    每项保留事件归属（event_id）与多信号透传。不适用事件 / 被排除选项不入榜。
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
                    pool=option.pool,
                    momentum=option.momentum,
                    fragility=option.fragility,
                    overheat_score=option.overheat_score,
                    watch_score=option.watch_score,
                )
            )

    overheated = [r for r in ranked if r.category in _OVERHEATED]
    watch = [r for r in ranked if r.category in _WATCH]
    reasonable = [r for r in ranked if r.category not in _OVERHEATED | _WATCH]

    overheated.sort(key=lambda r: r.overheat_score or 0.0, reverse=True)
    watch.sort(key=lambda r: (r.watch_score or 0.0, abs(r.bias)), reverse=True)

    return RankingResult(
        bubble_risk=overheated,
        value_opportunity=watch,
        fairly_priced=reasonable,
    )
