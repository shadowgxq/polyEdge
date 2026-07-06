"""bias_scoring 单测：黄金 fixture 回归 + 数值口径 + 排行分档 + 冒烟。

黄金 fixture（tests/fixtures/bias_golden.json）为算法回归基准（bias-algorithm §8、PRD AC-3），
数值人工精算并交叉核对；改动算法须同步更新样例与预期。
"""

import json
import math
from pathlib import Path

import pytest

from app.services.bias_scoring import (
    BiasParams,
    CATEGORY_LABELS,
    EventInput,
    Pool,
    compute_event_bias,
    norm,
    rank_options,
    round_half_away_from_zero,
)
from app.services.bias_scoring.labels import BiasCategory, classify

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bias_golden.json"


def _load_golden_cases() -> list[dict]:
    with _FIXTURE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)["cases"]


GOLDEN_CASES = _load_golden_cases()


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["name"] for c in GOLDEN_CASES])
def test_golden_fixture(case: dict):
    """逐条断言黄金 fixture 输入 → 期望 bias_i / 标签 / 事件级标注。"""
    params = BiasParams(**case["params"]) if case["params"] else BiasParams()
    event = EventInput(**case["event"])

    result = compute_event_bias(event, params)
    expected = case["expected"]

    assert result.applicable is expected["applicable"]
    assert result.not_applicable_reason == expected["not_applicable_reason"]
    assert result.degraded_trade_only is expected["degraded_trade_only"]

    result_by_id = {o.option_id: o for o in result.options}
    assert set(result_by_id) == {o["option_id"] for o in expected["options"]}

    for opt_exp in expected["options"]:
        opt = result_by_id[opt_exp["option_id"]]
        assert opt.excluded is opt_exp["excluded"], opt_exp["option_id"]
        assert opt.bias == opt_exp["bias"], opt_exp["option_id"]
        expected_category = (
            BiasCategory(opt_exp["category"]) if opt_exp["category"] else None
        )
        assert opt.category == expected_category, opt_exp["option_id"]
        # 有 bias 的选项必带中英两套文案；无则均为 None。
        if opt.bias is not None:
            assert opt.label_zh and opt.label_en
        else:
            assert opt.label_zh is None and opt.label_en is None


def test_round_half_away_from_zero_ties():
    """半值向上进位：.5 边界远离零方向，不走 banker's rounding。"""
    assert round_half_away_from_zero(14.5) == 15
    assert round_half_away_from_zero(-14.5) == -15
    assert round_half_away_from_zero(0.5) == 1
    assert round_half_away_from_zero(-0.5) == -1
    assert round_half_away_from_zero(2.5) == 3
    # 非 .5 边界正常四舍
    assert round_half_away_from_zero(14.4) == 14
    assert round_half_away_from_zero(-14.4) == -14


def test_norm_share_and_zero_guard():
    """norm 份额型：Σ>0 归一到和为 1；Σ=0 记 0 不产 NaN。"""
    shares = norm([60, 30, 10])
    assert math.isclose(sum(shares), 1.0)
    assert math.isclose(shares[0], 0.6)

    zeros = norm([0, 0, 0])
    assert zeros == [0.0, 0.0, 0.0]
    assert all(not math.isnan(x) for x in zeros)


def test_classify_thresholds():
    """三分类互斥：恰达 ±T 入档，阈值内为合理。"""
    assert classify(15, 15) == BiasCategory.BUBBLE_RISK
    assert classify(-15, 15) == BiasCategory.VALUE_OPPORTUNITY
    assert classify(14, 15) == BiasCategory.FAIRLY_PRICED
    assert classify(-14, 15) == BiasCategory.FAIRLY_PRICED


def test_clamp_defensive_truncation():
    """clamp 防御性截断：越界值截到 ±100（口径 bias-algorithm §3.7）。"""
    from app.services.bias_scoring.calculator import clamp

    assert clamp(round_half_away_from_zero(150.0), -100, 100) == 100
    assert clamp(round_half_away_from_zero(-150.0), -100, 100) == -100


def test_probability_shares_sum_to_one_on_valid_set():
    """有效选项集内 p_i 与 hs_i 各自归一到和为 1（排除无效后重归一）。"""
    event = EventInput(
        event_id="evt",
        options=[
            {"option_id": "A", "price": 0, "volume": 10, "traders": 5},
            {"option_id": "B", "price": 60, "volume": 30, "traders": 30},
            {"option_id": "C", "price": 40, "volume": 20, "traders": 20},
        ],
    )
    result = compute_event_bias(event)
    valid = [o for o in result.options if not o.excluded]
    assert math.isclose(sum(o.p for o in valid), 1.0)
    assert math.isclose(sum(o.hs for o in valid), 1.0)


def test_configurable_params_do_not_change_structure():
    """覆盖 α/β/T 只改数值不改结构：仍产出 bias 与三分类。"""
    event = EventInput(
        event_id="evt",
        options=[
            {"option_id": "A", "price": 55, "volume": 60, "traders": 50},
            {"option_id": "B", "price": 45, "volume": 40, "traders": 30},
        ],
    )
    default = compute_event_bias(event)
    custom = compute_event_bias(event, BiasParams(alpha=0.5, beta=0.5, threshold_t=5))
    assert default.applicable and custom.applicable
    assert all(o.bias is not None for o in custom.options)


def test_ranking_buckets_mutually_exclusive():
    """多事件排行：三榜按诚实标签互斥分档，并按对应复合分排序。"""
    events = [
        EventInput(
            event_id="overheat",
            options=[
                {
                    "option_id": "A",
                    "price": 0.45,
                    "volume": 100,
                    "liquidity": 50,
                    "volume24hr": 900,
                    "volume1wk": 700,
                    "one_day_price_change": 0.10,
                    "spread": 0.04,
                    "traders": None,
                },
                {
                    "option_id": "B",
                    "price": 0.35,
                    "volume": 100,
                    "liquidity": 50,
                    "volume24hr": 50,
                    "volume1wk": 700,
                    "spread": 0.001,
                    "traders": None,
                },
                {
                    "option_id": "C",
                    "price": 0.20,
                    "volume": 100,
                    "liquidity": 50,
                    "volume24hr": 50,
                    "volume1wk": 700,
                    "spread": 0.001,
                    "traders": None,
                },
            ],
        ),
        EventInput(
            event_id="longshot",
            options=[
                {
                    "option_id": "A",
                    "price": 0.45,
                    "volume": 1000,
                    "liquidity": 100,
                    "volume24hr": 500,
                    "volume1wk": 3500,
                    "traders": None,
                },
                {
                    "option_id": "B",
                    "price": 0.35,
                    "volume": 1000,
                    "liquidity": 100,
                    "volume24hr": 500,
                    "volume1wk": 3500,
                    "traders": None,
                },
                {
                    "option_id": "C",
                    "price": 0.15,
                    "volume": 1000,
                    "liquidity": 100,
                    "volume24hr": 500,
                    "volume1wk": 3500,
                    "traders": None,
                },
                {
                    "option_id": "D",
                    "price": 0.05,
                    "volume": 100,
                    "liquidity": 3000,
                    "volume24hr": 1,
                    "volume1wk": 7,
                    "one_day_price_change": 0.02,
                    "spread": 0.0005,
                    "traders": None,
                },
            ],
        ),
    ]
    ranking = rank_options(events)

    all_items = ranking.bubble_risk + ranking.value_opportunity + ranking.fairly_priced
    keys = [(item.event_id, item.option_id) for item in all_items]
    assert len(keys) == 7  # 无遗漏
    assert len(keys) == len(set(keys))  # 无重复（互斥）

    assert {item.category for item in ranking.bubble_risk} == {
        BiasCategory.OVERHEATED_FAVORITE
    }
    assert {item.category for item in ranking.value_opportunity} == {
        BiasCategory.LOW_ATTENTION_FAVORITE,
        BiasCategory.WATCH_LONGSHOT,
    }
    assert all(
        item.category in {BiasCategory.CONSENSUS_FAVORITE, BiasCategory.CONTENDER}
        for item in ranking.fairly_priced
    )
    assert [i.overheat_score for i in ranking.bubble_risk] == sorted(
        (i.overheat_score for i in ranking.bubble_risk), reverse=True
    )
    assert [
        (i.watch_score or 0.0, abs(i.bias)) for i in ranking.value_opportunity
    ] == sorted(
        ((i.watch_score or 0.0, abs(i.bias)) for i in ranking.value_opportunity),
        reverse=True,
    )
    # 事件归属保留
    assert all(item.event_id in {"overheat", "longshot"} for item in all_items)


def test_favorite_low_attention_not_classified_as_longshot():
    """头号热门即使关注不足，也只能是低关注热门，不得进入冷门池。"""
    event = EventInput(
        event_id="world-cup-winner",
        options=[
            {
                "option_id": "France",
                "price": 0.3275,
                "volume": 96_339_712.96,
                "liquidity": 8_168_879.65,
                "volume24hr": 1_780_159.15,
                "volume1wk": 17_415_683.98,
                "one_day_price_change": -0.026,
                "spread": 0.001,
                "traders": None,
            },
            {
                "option_id": "Argentina",
                "price": 0.1665,
                "volume": 101_950_515.19,
                "liquidity": 7_775_079.47,
                "volume24hr": 2_082_873.40,
                "volume1wk": 19_781_962.46,
                "one_day_price_change": -0.001,
                "spread": 0.001,
                "traders": None,
            },
            {
                "option_id": "England",
                "price": 0.1405,
                "volume": 83_512_424.93,
                "liquidity": 5_942_656.05,
                "volume24hr": 4_902_293.33,
                "volume1wk": 21_272_459.04,
                "one_day_price_change": 0.069,
                "spread": 0.001,
                "traders": None,
            },
            {
                "option_id": "Spain",
                "price": 0.1275,
                "volume": 87_179_312.71,
                "liquidity": 6_912_131.78,
                "volume24hr": 2_144_168.32,
                "volume1wk": 17_258_330.64,
                "one_day_price_change": 0.004,
                "spread": 0.001,
                "traders": None,
            },
        ],
    )
    result = compute_event_bias(event)
    france = next(o for o in result.options if o.option_id == "France")

    assert france.pool is Pool.FAVORITE
    assert france.category is BiasCategory.LOW_ATTENTION_FAVORITE
    assert france.label_zh == "低关注热门"
    assert "冷门" not in france.label_zh
    assert france.watch_score is None


def test_favorite_overheat_uses_multi_signal_score():
    """热门池过热由 attention residual + 动量 / 脆弱 / 加速综合触发。"""
    event = EventInput(
        event_id="favorite-overheat",
        options=[
            {
                "option_id": "A",
                "price": 0.45,
                "volume": 100,
                "liquidity": 50,
                "volume24hr": 900,
                "volume1wk": 700,
                "one_day_price_change": 0.10,
                "spread": 0.04,
                "traders": None,
            },
            {
                "option_id": "B",
                "price": 0.35,
                "volume": 100,
                "liquidity": 50,
                "volume24hr": 50,
                "volume1wk": 700,
                "spread": 0.001,
                "traders": None,
            },
            {
                "option_id": "C",
                "price": 0.20,
                "volume": 100,
                "liquidity": 50,
                "volume24hr": 50,
                "volume1wk": 700,
                "spread": 0.001,
                "traders": None,
            },
        ],
    )
    a = compute_event_bias(event).options[0]

    assert a.pool is Pool.FAVORITE
    assert a.category is BiasCategory.OVERHEATED_FAVORITE
    assert a.overheat_score is not None and a.overheat_score >= 60


def test_longshot_hyped_and_watch_gates_are_distinct():
    """冷门池内，拥挤优先判被炒作；不拥挤但流动性健康才判观察冷门。"""
    hyped = EventInput(
        event_id="hyped",
        options=[
            {
                "option_id": "A",
                "price": 0.45,
                "volume": 100,
                "liquidity": 500,
                "volume24hr": 100,
                "volume1wk": 700,
                "traders": None,
            },
            {
                "option_id": "B",
                "price": 0.35,
                "volume": 100,
                "liquidity": 500,
                "volume24hr": 100,
                "volume1wk": 700,
                "traders": None,
            },
            {
                "option_id": "C",
                "price": 0.15,
                "volume": 100,
                "liquidity": 500,
                "volume24hr": 100,
                "volume1wk": 700,
                "traders": None,
            },
            {
                "option_id": "D",
                "price": 0.05,
                "volume": 100,
                "liquidity": 500,
                "volume24hr": 900,
                "volume1wk": 700,
                "one_day_price_change": 0.08,
                "spread": 0.001,
                "traders": None,
            },
        ],
    )
    watch = EventInput(
        event_id="watch",
        options=[
            {
                "option_id": "A",
                "price": 0.45,
                "volume": 1000,
                "liquidity": 100,
                "volume24hr": 500,
                "volume1wk": 3500,
                "traders": None,
            },
            {
                "option_id": "B",
                "price": 0.35,
                "volume": 1000,
                "liquidity": 100,
                "volume24hr": 500,
                "volume1wk": 3500,
                "traders": None,
            },
            {
                "option_id": "C",
                "price": 0.15,
                "volume": 1000,
                "liquidity": 100,
                "volume24hr": 500,
                "volume1wk": 3500,
                "traders": None,
            },
            {
                "option_id": "D",
                "price": 0.05,
                "volume": 100,
                "liquidity": 3000,
                "volume24hr": 1,
                "volume1wk": 7,
                "one_day_price_change": 0.02,
                "spread": 0.0005,
                "traders": None,
            },
        ],
    )

    hyped_d = next(o for o in compute_event_bias(hyped).options if o.option_id == "D")
    watch_d = next(o for o in compute_event_bias(watch).options if o.option_id == "D")

    assert hyped_d.pool is Pool.LONGSHOT
    assert hyped_d.category is BiasCategory.HYPED_LONGSHOT
    assert hyped_d.watch_score is not None and hyped_d.watch_score >= 55
    assert watch_d.pool is Pool.LONGSHOT
    assert watch_d.bias is not None and watch_d.bias < 15
    assert watch_d.category is BiasCategory.WATCH_LONGSHOT
    assert watch_d.watch_score is not None and watch_d.watch_score >= 55


def test_missing_multisignal_fields_fallback_to_neutral():
    """白拿字段缺失时，多信号按 0 兜底，不产生 NaN 或异常分。"""
    event = EventInput(
        event_id="missing-fields",
        options=[
            {
                "option_id": "A",
                "price": 0.5,
                "volume": 100,
                "liquidity": 100,
                "volume24hr": 100,
                "traders": None,
            },
            {
                "option_id": "B",
                "price": 0.5,
                "volume": 100,
                "liquidity": 100,
                "volume24hr": 100,
                "traders": None,
            },
        ],
    )
    result = compute_event_bias(event)

    assert result.applicable
    for option in result.options:
        assert option.momentum == 0.0
        assert option.fragility == 0.0
        assert option.overheat_score == 0.0
        assert option.category is BiasCategory.CONSENSUS_FAVORITE
        assert option.watch_score is None


def test_category_labels_do_not_claim_value_mispricing():
    """新旧标签文案都不宣称相对真实概率的高估/低估。"""
    forbidden = ("高估", "低估", "冷门机会", "undervalued", "overvalued", "fair value")
    for labels in CATEGORY_LABELS.values():
        text = f"{labels['zh']} {labels['en']}".lower()
        assert all(term not in text for term in forbidden)


def test_smoke_realistic_no_nan_no_raise():
    """冒烟：近真实数据不产 NaN、不抛异常、输出结构完整（不断言具体 bias 数值）。"""
    event = EventInput(
        event_id="0x-real",
        comment_count=128,
        options=[
            {
                "option_id": "yes",
                "label": "Yes",
                "price": 0.62,
                "volume": 1_284_512.44,
                "liquidity": 84_120.11,
                "volume24hr": 53_221.7,
                "traders": 4123,
            },
            {
                "option_id": "no",
                "label": "No",
                "price": 0.38,
                "volume": 902_144.9,
                "liquidity": 51_004.02,
                "volume24hr": 41_889.31,
                "traders": 3011,
            },
        ],
    )
    result = compute_event_bias(event)
    assert result.applicable
    for opt in result.options:
        assert opt.bias is not None
        assert -100 <= opt.bias <= 100
        for value in (opt.p, opt.trade, opt.h, opt.hs, opt.d):
            assert value is not None and not math.isnan(value)
