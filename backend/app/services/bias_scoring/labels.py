"""偏差三分类标签（bias-algorithm §4、PRD §5.4）。

阈值 T 三档互斥无交集；每个标签同时产出中 / 英两套文案供前端 i18n。
"""

from enum import Enum


class BiasCategory(str, Enum):
    """偏差三分类档位 key。"""

    BUBBLE_RISK = "bubble_risk"  # 高热度·泡沫风险
    VALUE_OPPORTUNITY = "value_opportunity"  # 低热度·冷门机会
    FAIRLY_PRICED = "fairly_priced"  # 合理


# 中 / 英两套文案（bias-algorithm §4）。前端按当前语言渲染。
CATEGORY_LABELS: dict[BiasCategory, dict[str, str]] = {
    BiasCategory.BUBBLE_RISK: {
        "zh": "高热度·泡沫风险",
        "en": "Overheated · Bubble Risk",
    },
    BiasCategory.VALUE_OPPORTUNITY: {
        "zh": "低热度·冷门机会",
        "en": "Underhyped · Value Opportunity",
    },
    BiasCategory.FAIRLY_PRICED: {"zh": "合理", "en": "Fairly Priced"},
}


def classify(bias: int, threshold: int) -> BiasCategory:
    """按阈值 T 对 bias_i 三分类（互斥无交集，bias-algorithm §4）。

    - ``bias >= +T`` → 泡沫风险
    - ``bias <= -T`` → 冷门机会
    - ``-T < bias < +T`` → 合理
    """
    if bias >= threshold:
        return BiasCategory.BUBBLE_RISK
    if bias <= -threshold:
        return BiasCategory.VALUE_OPPORTUNITY
    return BiasCategory.FAIRLY_PRICED


def label_zh(category: BiasCategory) -> str:
    """返回中文标签文案。"""
    return CATEGORY_LABELS[category]["zh"]


def label_en(category: BiasCategory) -> str:
    """返回英文标签文案。"""
    return CATEGORY_LABELS[category]["en"]
