"""bias_scoring：单事件内「热度份额 vs 概率份额」偏差计算的纯规则口径。

对外聚合导出：输入契约、参数、计算主链路、三分类标签与多事件排行分档。
口径锚定 bias-algorithm §3–§8，纯计算无副作用（design D1）。
"""

from app.services.bias_scoring.calculator import (
    compute_event_bias,
    norm,
    round_half_away_from_zero,
)
from app.services.bias_scoring.contracts import EventInput, OptionInput
from app.services.bias_scoring.labels import (
    CATEGORY_LABELS,
    BiasCategory,
    classify,
    label_en,
    label_zh,
)
from app.services.bias_scoring.params import DEFAULT_PARAMS, BiasParams
from app.services.bias_scoring.ranking import rank_options
from app.services.bias_scoring.results import (
    EventBiasResult,
    OptionBiasResult,
    RankedOption,
    RankingResult,
)

__all__ = [
    "CATEGORY_LABELS",
    "DEFAULT_PARAMS",
    "BiasCategory",
    "BiasParams",
    "EventBiasResult",
    "EventInput",
    "OptionBiasResult",
    "OptionInput",
    "RankedOption",
    "RankingResult",
    "classify",
    "compute_event_bias",
    "label_en",
    "label_zh",
    "norm",
    "rank_options",
    "round_half_away_from_zero",
]
