"""偏差标签体系（bias-algorithm §4、bias-multi-signal）。

诚实底线：只用 Polymarket 自身数据，标签与文案不宣称「相对真实概率的高估/低估」，
只表达身份（热门/中位/冷门）与内部结构信号（拥挤 / 过热 / 值得观察）。

- 八类诚实标签由 `classify_option(...)` 依「身份池 × crowding × overheat × watch × 阈值 T」产出。
- 旧三分类 `classify(bias, T)` 与 `BUBBLE_RISK/VALUE_OPPORTUNITY/FAIRLY_PRICED` 保留，
  供既有纯函数单测与向后兼容，不在新链路产出。
"""

from enum import Enum


class Pool(str, Enum):
    """身份池：由市场概率份额决定，不由热度决定（bias-multi-signal design D3）。"""

    FAVORITE = "favorite"  # 热门池
    CONTENDER = "contender"  # 中位池
    LONGSHOT = "longshot"  # 冷门池


class BiasCategory(str, Enum):
    """偏差标签档位 key。

    前三项为旧三分类（保留兼容 / 既有单测）；后八项为诚实多信号标签（新链路产出）。
    """

    # —— 旧三分类（保留，不在新链路产出） ——
    BUBBLE_RISK = "bubble_risk"
    VALUE_OPPORTUNITY = "value_opportunity"
    FAIRLY_PRICED = "fairly_priced"

    # —— 八类诚实标签（bias-multi-signal） ——
    CONSENSUS_FAVORITE = "consensus_favorite"  # 共识热门
    LOW_ATTENTION_FAVORITE = "low_attention_favorite"  # 低关注热门
    OVERHEATED_FAVORITE = "overheated_favorite"  # 过热热门
    CONTENDER = "contender"  # 中位竞争者
    OVERHEATED_CONTENDER = "overheated_contender"  # 过热中位
    QUIET_LONGSHOT = "quiet_longshot"  # 普通冷门
    HYPED_LONGSHOT = "hyped_longshot"  # 被炒作冷门
    WATCH_LONGSHOT = "watch_longshot"  # 观察冷门


# 中 / 英双文案。诚实底线：不出现「高估/低估/undervalued/overvalued」等措辞。
CATEGORY_LABELS: dict[BiasCategory, dict[str, str]] = {
    # 旧三分类（保留兼容；新链路不产出，文案也保持中性避免价值宣称）
    BiasCategory.BUBBLE_RISK: {
        "zh": "高关注·拥挤信号",
        "en": "Crowded Attention Signal",
    },
    BiasCategory.VALUE_OPPORTUNITY: {
        "zh": "低关注·观察信号",
        "en": "Low-attention Watch Signal",
    },
    BiasCategory.FAIRLY_PRICED: {"zh": "结构正常", "en": "Normal Structure"},
    # 八类诚实标签
    BiasCategory.CONSENSUS_FAVORITE: {"zh": "共识热门", "en": "Consensus Favorite"},
    BiasCategory.LOW_ATTENTION_FAVORITE: {
        "zh": "低关注热门",
        "en": "Low-attention Favorite",
    },
    BiasCategory.OVERHEATED_FAVORITE: {"zh": "过热热门", "en": "Overheated Favorite"},
    BiasCategory.CONTENDER: {"zh": "中位竞争者", "en": "Contender"},
    BiasCategory.OVERHEATED_CONTENDER: {"zh": "过热中位", "en": "Overheated Contender"},
    BiasCategory.QUIET_LONGSHOT: {"zh": "普通冷门", "en": "Quiet Longshot"},
    BiasCategory.HYPED_LONGSHOT: {"zh": "被炒作冷门", "en": "Hyped Longshot"},
    BiasCategory.WATCH_LONGSHOT: {"zh": "观察冷门", "en": "Watch Longshot"},
}


def classify(bias: int, threshold: int) -> BiasCategory:
    """旧三分类（保留兼容 / 既有单测，bias-algorithm §4）。

    - ``bias >= +T`` → 高关注兼容档
    - ``bias <= -T`` → 低关注兼容档
    - ``-T < bias < +T`` → 中性兼容档
    """
    if bias >= threshold:
        return BiasCategory.BUBBLE_RISK
    if bias <= -threshold:
        return BiasCategory.VALUE_OPPORTUNITY
    return BiasCategory.FAIRLY_PRICED


def classify_option(
    pool: Pool,
    crowding: float,
    overheat_score: float,
    watch_score: float,
    threshold: int,
    *,
    overheat_hi: int,
    watch_hi: int,
) -> BiasCategory:
    """八类诚实标签决策（bias-multi-signal design D6）。

    ``threshold`` 为 crowding×100 的阈值 T（与 bias 同标度）；比较用 ``crowding*100``。
    """
    crowd_score = crowding * 100

    if pool is Pool.FAVORITE:
        if overheat_score >= overheat_hi:
            return BiasCategory.OVERHEATED_FAVORITE
        if crowd_score <= -threshold:
            return BiasCategory.LOW_ATTENTION_FAVORITE
        return BiasCategory.CONSENSUS_FAVORITE

    if pool is Pool.CONTENDER:
        if overheat_score >= overheat_hi:
            return BiasCategory.OVERHEATED_CONTENDER
        return BiasCategory.CONTENDER

    # Pool.LONGSHOT
    if crowd_score >= threshold:
        return BiasCategory.HYPED_LONGSHOT
    if watch_score >= watch_hi:
        return BiasCategory.WATCH_LONGSHOT
    return BiasCategory.QUIET_LONGSHOT


def label_zh(category: BiasCategory) -> str:
    """返回中文标签文案。"""
    return CATEGORY_LABELS[category]["zh"]


def label_en(category: BiasCategory) -> str:
    """返回英文标签文案。"""
    return CATEGORY_LABELS[category]["en"]
