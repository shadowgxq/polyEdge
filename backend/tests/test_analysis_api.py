"""analysis-api 组合层测试：默认列表概览标签、单事件明细退化/排除/不适用、
slug 解析成功/未找到、搜索上游/本地回退/空候选、排行三榜互斥/TopN/空榜、
上游不可用转错误态、实时限流超阈值 429 与 fail-open。

用 duck-typed 的 FakeMarketData 替换 poly-data-integration 的 MarketDataService，
不依赖真实 Redis / Polymarket。
"""

from datetime import datetime, timezone

import pytest
from redis.exceptions import RedisError

import app.services.rate_limit_service as rate_limit_module
from app.api.v1 import events as events_route
from app.api.v1 import rankings as rankings_route
from app.core.exceptions import (
    EventNotFoundException,
    UpstreamUnavailableException,
)
from app.schemas.analysis import EventCategory, SearchScope
from app.schemas.market_data import MarketEvent, MarketOption, PriceSource
from app.services.analysis_service import AnalysisService
from app.services.rate_limit_service import RateLimitService

_SNAPSHOT = datetime(2026, 7, 6, tzinfo=timezone.utc)


def _option(outcome, price, volume, traders=100, icon_url=None):
    return MarketOption(
        outcome=outcome,
        icon_url=icon_url,
        price=price,
        price_source=PriceSource.CLOB_MIDPOINT,
        volume=volume,
        liquidity=volume,
        volume24hr=volume,
        traders=traders,
    )


def _signal_option(
    outcome,
    price,
    volume,
    *,
    liquidity=None,
    volume24hr=None,
    volume1wk=None,
    one_day_price_change=None,
    spread=None,
    traders=None,
):
    return MarketOption(
        outcome=outcome,
        price=price,
        price_source=PriceSource.OUTCOME_PRICES_FALLBACK,
        volume=volume,
        liquidity=liquidity if liquidity is not None else volume,
        volume24hr=volume24hr if volume24hr is not None else volume,
        volume1wk=volume1wk,
        one_day_price_change=one_day_price_change,
        spread=spread,
        traders=traders,
    )


def _skewed_event(slug="hot-event", title="Hot Event"):
    """Yes 交易关注高于价格份额，No 反向。"""
    return MarketEvent(
        slug=slug,
        title=title,
        comment_count=7,
        options=[
            _option("Yes", 0.5, 9000, traders=900),
            _option("No", 0.5, 1000, traders=100),
        ],
        data_snapshot_at=_SNAPSHOT,
    )


def _fair_event(slug="fair-event", title="Fair Event"):
    return MarketEvent(
        slug=slug,
        title=title,
        comment_count=3,
        options=[
            _option("Yes", 0.5, 5000, traders=500),
            _option("No", 0.5, 5000, traders=500),
        ],
        data_snapshot_at=_SNAPSHOT,
    )


def _overheat_event(slug="overheat-event", title="Overheat Event"):
    return MarketEvent(
        slug=slug,
        title=title,
        options=[
            _signal_option(
                "A",
                0.45,
                100,
                liquidity=50,
                volume24hr=900,
                volume1wk=700,
                one_day_price_change=0.10,
                spread=0.04,
            ),
            _signal_option(
                "B",
                0.35,
                100,
                liquidity=50,
                volume24hr=50,
                volume1wk=700,
                spread=0.001,
            ),
            _signal_option(
                "C",
                0.20,
                100,
                liquidity=50,
                volume24hr=50,
                volume1wk=700,
                spread=0.001,
            ),
        ],
        data_snapshot_at=_SNAPSHOT,
    )


def _watch_event(slug="watch-event", title="Watch Event"):
    return MarketEvent(
        slug=slug,
        title=title,
        options=[
            _signal_option(
                "A", 0.45, 1000, liquidity=100, volume24hr=500, volume1wk=3500
            ),
            _signal_option(
                "B", 0.35, 1000, liquidity=100, volume24hr=500, volume1wk=3500
            ),
            _signal_option(
                "C", 0.15, 1000, liquidity=100, volume24hr=500, volume1wk=3500
            ),
            _signal_option(
                "D",
                0.05,
                100,
                liquidity=3000,
                volume24hr=1,
                volume1wk=7,
                one_day_price_change=0.02,
                spread=0.0005,
            ),
        ],
        data_snapshot_at=_SNAPSHOT,
    )


def _world_cup_low_attention_favorite_event():
    return MarketEvent(
        slug="world-cup-winner",
        title="World Cup Winner",
        options=[
            _signal_option(
                "France",
                0.3275,
                96_339_712.96,
                liquidity=8_168_879.65,
                volume24hr=1_780_159.15,
                volume1wk=17_415_683.98,
                one_day_price_change=-0.026,
                spread=0.001,
            ),
            _signal_option(
                "Argentina",
                0.1665,
                101_950_515.19,
                liquidity=7_775_079.47,
                volume24hr=2_082_873.40,
                volume1wk=19_781_962.46,
                one_day_price_change=-0.001,
                spread=0.001,
            ),
            _signal_option(
                "England",
                0.1405,
                83_512_424.93,
                liquidity=5_942_656.05,
                volume24hr=4_902_293.33,
                volume1wk=21_272_459.04,
                one_day_price_change=0.069,
                spread=0.001,
            ),
            _signal_option(
                "Spain",
                0.1275,
                87_179_312.71,
                liquidity=6_912_131.78,
                volume24hr=2_144_168.32,
                volume1wk=17_258_330.64,
                one_day_price_change=0.004,
                spread=0.001,
            ),
        ],
        data_snapshot_at=_SNAPSHOT,
    )


class FakeMarketData:
    """duck-typed 替身，行为等价 MarketDataService 的读取接口。"""

    def __init__(self, *, event=None, popular=None, world_cup=None, fail=False):
        self._event = event
        self._popular = popular or []
        self._world_cup = world_cup or []
        self._fail = fail

    def get_event(self, slug, *, force_refresh=False):
        if self._fail:
            raise UpstreamUnavailableException()
        if self._event is not None and self._event.slug == slug:
            return self._event
        raise UpstreamUnavailableException()

    def get_popular_events(self, limit=None, *, force_refresh=False):
        if self._fail:
            raise UpstreamUnavailableException()
        return self._popular

    def get_world_cup_events(self, limit=None, *, force_refresh=False):
        if self._fail:
            raise UpstreamUnavailableException()
        return self._world_cup


# ---------------- 单事件明细：正常 / 退化 / 排除 / 不适用 ----------------


def test_event_detail_returns_option_bias_and_labels():
    event = _skewed_event()
    event.options[0].icon_url = "https://polymarket-upload.s3.us-east-2.amazonaws.com/yes.png"
    service = AnalysisService(FakeMarketData(event=event))
    detail = service.get_event_detail("hot-event")

    assert detail.applicable is True
    assert detail.degraded_trade_only is False
    assert detail.comment_count == 7
    assert detail.data_snapshot_at == _SNAPSHOT
    yes = next(o for o in detail.options if o.name == "Yes")
    assert yes.icon_url == "https://polymarket-upload.s3.us-east-2.amazonaws.com/yes.png"
    assert yes.bias_score is not None and yes.bias_score > 0
    assert yes.label is not None and yes.label.zh and yes.label.en


def test_event_detail_degraded_trade_only_when_participation_missing():
    event = MarketEvent(
        slug="degraded",
        title="Degraded",
        options=[
            _option("Yes", 0.6, 9000, traders=None),
            _option("No", 0.4, 1000, traders=None),
        ],
        data_snapshot_at=_SNAPSHOT,
    )
    detail = AnalysisService(FakeMarketData(event=event)).get_event_detail("degraded")
    assert detail.applicable is True
    assert detail.degraded_trade_only is True


def test_event_detail_marks_excluded_option():
    event = MarketEvent(
        slug="excl",
        title="Excl",
        options=[
            _option("A", 0.5, 5000),
            _option("B", 0.5, 5000),
            _option("C", 0.0, 0),
        ],
        data_snapshot_at=_SNAPSHOT,
    )
    detail = AnalysisService(FakeMarketData(event=event)).get_event_detail("excl")
    c = next(o for o in detail.options if o.name == "C")
    assert c.excluded is True
    assert c.bias_score is None


def test_event_detail_not_applicable_single_valid_option():
    event = MarketEvent(
        slug="single",
        title="Single",
        options=[
            _option("Yes", 0.7, 5000),
            _option("No", 0.0, 0),
        ],
        data_snapshot_at=_SNAPSHOT,
    )
    detail = AnalysisService(FakeMarketData(event=event)).get_event_detail("single")
    assert detail.applicable is False
    assert all(o.bias_score is None for o in detail.options)


# ---------------- 默认列表：分类 + 概览标签 + 分页 ----------------


def test_event_list_overview_label_takes_max_abs_bias_option():
    service = AnalysisService(FakeMarketData(popular=[_skewed_event()], world_cup=[]))
    result = service.get_event_list(EventCategory.HOT, page=1, page_size=20)
    assert result.category is EventCategory.HOT
    card = result.items[0]
    assert card.applicable is True
    # |bias| 并列时 tie-break 取更大 volume 的 Yes
    assert card.overview_option_name == "Yes"
    assert card.overview_label is not None


def test_event_list_favorite_low_attention_overview_is_not_longshot():
    service = AnalysisService(
        FakeMarketData(popular=[_world_cup_low_attention_favorite_event()])
    )
    card = service.get_event_list(EventCategory.HOT, page=1, page_size=20).items[0]

    assert card.overview_option_name == "France"
    assert card.overview_label is not None
    assert card.overview_label.zh == "低关注热门"
    assert "冷门" not in card.overview_label.zh


def test_event_list_not_applicable_card_has_null_label():
    event = MarketEvent(
        slug="na",
        title="NA",
        options=[_option("Yes", 0.7, 5000), _option("No", 0.0, 0)],
        data_snapshot_at=_SNAPSHOT,
    )
    service = AnalysisService(FakeMarketData(popular=[event]))
    card = service.get_event_list(EventCategory.HOT, 1, 20).items[0]
    assert card.applicable is False
    assert card.overview_label is None
    assert card.overview_option_name is None


def test_event_list_world_cup_empty_returns_empty_items():
    service = AnalysisService(FakeMarketData(world_cup=[]))
    result = service.get_event_list(EventCategory.WORLD_CUP, 1, 20)
    assert result.items == []
    assert result.total_count == 0
    assert result.has_more is False


def test_event_list_pagination_has_more():
    events = [_skewed_event(slug=f"e{i}", title=f"E{i}") for i in range(3)]
    service = AnalysisService(FakeMarketData(popular=events))
    result = service.get_event_list(EventCategory.HOT, page=1, page_size=2)
    assert len(result.items) == 2
    assert result.total_count == 3
    assert result.has_more is True


def test_event_card_previews_top_options_by_probability():
    # 多候选事件：卡片按概率降序只露 TopN 预览，options_total 记全量供「+N 更多」。
    options = [_option(f"Team{i}", price=i / 100, volume=1000 - i) for i in range(12)]
    event = MarketEvent(
        slug="many",
        title="Many candidates",
        options=options,
        data_snapshot_at=_SNAPSHOT,
    )
    service = AnalysisService(FakeMarketData(popular=[event]))
    card = service.get_event_list(EventCategory.HOT, 1, 20).items[0]

    assert card.options_total == 12
    assert len(card.options) == 5  # event_card_option_preview 默认 5
    prices = [option.price for option in card.options]
    assert prices == sorted(prices, reverse=True)  # 概率降序
    assert card.options[0].name == "Team11"  # 概率最高者置顶


# ---------------- slug 解析 ----------------


def test_resolve_event_from_url():
    service = AnalysisService(FakeMarketData(event=_skewed_event(slug="hot-event")))
    detail = service.resolve_event("https://polymarket.com/event/hot-event")
    assert detail.slug == "hot-event"


def test_resolve_event_from_bare_slug():
    service = AnalysisService(FakeMarketData(event=_skewed_event(slug="hot-event")))
    detail = service.resolve_event("hot-event")
    assert detail.slug == "hot-event"


def test_resolve_event_invalid_input_raises_not_found():
    service = AnalysisService(FakeMarketData())
    with pytest.raises(EventNotFoundException):
        service.resolve_event("   ")


# ---------------- 名称搜索 ----------------


def test_search_local_cache_fuzzy_match():
    service = AnalysisService(
        FakeMarketData(
            popular=[_skewed_event(slug="world-cup-final", title="World Cup Final")]
        )
    )
    result = service.search_events("world cup")
    assert result.search_scope is SearchScope.LOCAL_CACHE
    assert result.candidates[0].slug == "world-cup-final"


def test_search_upstream_scope_when_available():
    def upstream(term, limit):
        return [_skewed_event(slug="up-1", title=f"Upstream {term}")]

    service = AnalysisService(FakeMarketData(), upstream_search=upstream)
    result = service.search_events("anything")
    assert result.search_scope is SearchScope.UPSTREAM
    assert result.candidates[0].slug == "up-1"


def test_search_no_match_returns_empty_with_scope():
    service = AnalysisService(FakeMarketData(popular=[_skewed_event(title="Foo")]))
    result = service.search_events("zzz-none")
    assert result.candidates == []
    assert result.search_scope is SearchScope.LOCAL_CACHE


# ---------------- 排行三榜 ----------------


def test_rankings_boards_mutually_exclusive_and_sorted():
    service = AnalysisService(
        FakeMarketData(popular=[_overheat_event(), _watch_event()])
    )
    boards = service.get_rankings(EventCategory.HOT, top_n=10)

    keys = [
        (i.event_slug, i.option_name)
        for board in (boards.bubble, boards.underhyped, boards.fair)
        for i in board
    ]
    assert len(keys) == len(set(keys))  # 无交集
    assert {i.label.zh for i in boards.bubble} == {"过热热门"}
    assert {i.label.zh for i in boards.underhyped} == {"观察冷门", "低关注热门"}
    assert all(i.label.zh == "共识热门" for i in boards.fair)
    # 过热榜按 overheat_score 降序，观察榜按 watch_score/|bias| 降序。
    assert boards.bubble == sorted(
        boards.bubble, key=lambda i: i.overheat_score or 0.0, reverse=True
    )
    assert boards.underhyped == sorted(
        boards.underhyped,
        key=lambda i: (i.watch_score or 0.0, abs(i.bias_score)),
        reverse=True,
    )


def test_rankings_topn_truncation():
    events = [_skewed_event(slug=f"s{i}", title=f"S{i}") for i in range(5)]
    service = AnalysisService(FakeMarketData(popular=events))
    boards = service.get_rankings(EventCategory.HOT, top_n=1)
    assert len(boards.bubble) <= 1
    assert len(boards.underhyped) <= 1


def test_rankings_empty_board_returns_list():
    service = AnalysisService(FakeMarketData(popular=[_fair_event()]))
    boards = service.get_rankings(EventCategory.HOT, top_n=10)
    assert boards.bubble == []
    assert boards.underhyped == []
    assert len(boards.fair) >= 1


# ---------------- API 层：错误态 + 限流 ----------------


def _override_analysis(fake):
    def _factory():
        return AnalysisService(fake)

    return _factory


class _NoopRefreshScheduler:
    def schedule_event(self, background_tasks, slug):
        return None

    def schedule_list(self, background_tasks, name):
        return None


def _override_refresh_scheduler():
    return _NoopRefreshScheduler()


def test_api_upstream_unavailable_maps_to_error_state(client):
    from main import app

    app.dependency_overrides[events_route.get_analysis_service] = _override_analysis(
        FakeMarketData(fail=True)
    )
    app.dependency_overrides[events_route.get_market_refresh_scheduler] = (
        _override_refresh_scheduler
    )
    resp = client.get("/api/v1/events/anything")
    assert resp.status_code == 503
    assert resp.json()["code"] == 50301


def test_api_event_list_success_envelope(client):
    from main import app

    app.dependency_overrides[events_route.get_analysis_service] = _override_analysis(
        FakeMarketData(popular=[_skewed_event()])
    )
    app.dependency_overrides[events_route.get_market_refresh_scheduler] = (
        _override_refresh_scheduler
    )
    resp = client.get("/api/v1/events?category=hot")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["items"][0]["slug"] == "hot-event"


def test_api_rankings_success_envelope(client):
    from main import app

    app.dependency_overrides[rankings_route.get_analysis_service] = _override_analysis(
        FakeMarketData(popular=[_skewed_event()])
    )
    app.dependency_overrides[rankings_route.get_market_refresh_scheduler] = (
        _override_refresh_scheduler
    )
    resp = client.get("/api/v1/rankings?category=hot")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_api_realtime_rate_limit_exceeds_returns_429(client, fake_redis, monkeypatch):
    from main import app

    monkeypatch.setattr(rate_limit_module, "redis_client", fake_redis)
    app.dependency_overrides[events_route.get_analysis_service] = _override_analysis(
        FakeMarketData(popular=[_skewed_event(title="World")])
    )
    app.dependency_overrides[events_route.get_market_refresh_scheduler] = (
        _override_refresh_scheduler
    )
    app.dependency_overrides[events_route.get_rate_limit_service] = lambda: (
        RateLimitService(window_seconds=60, max_requests=1)
    )
    first = client.get("/api/v1/events/search?q=world")
    second = client.get("/api/v1/events/search?q=world")
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == 42902


def test_api_realtime_rate_limit_fail_open_on_redis_error(client, monkeypatch):
    from main import app

    class BrokenRedis:
        def incr(self, key):
            raise RedisError("down")

        def expire(self, key, seconds):
            raise RedisError("down")

    monkeypatch.setattr(rate_limit_module, "redis_client", BrokenRedis())
    app.dependency_overrides[events_route.get_analysis_service] = _override_analysis(
        FakeMarketData(popular=[_skewed_event(title="World")])
    )
    app.dependency_overrides[events_route.get_market_refresh_scheduler] = (
        _override_refresh_scheduler
    )
    app.dependency_overrides[events_route.get_rate_limit_service] = lambda: (
        RateLimitService(window_seconds=60, max_requests=1)
    )
    # 多次请求都不应被拦截（计数降级为 0，fail-open）
    for _ in range(3):
        resp = client.get("/api/v1/events/search?q=world")
        assert resp.status_code == 200
