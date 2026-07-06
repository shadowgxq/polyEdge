"""market-data 数据接入测试：归一映射、价源回退、粒度兜底、参与谓词三态、
分层 TTL、退避重试、失败回退缓存 / 无缓存报错、预取入缓存、DB 快照持久层。"""

from datetime import datetime, timezone

import httpx
import pytest

import app.repositories.market_data_cache_repository as cache_module
from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableException
from app.repositories.market_data_cache_repository import MarketDataCacheRepository
from app.repositories.market_snapshot_repository import MarketSnapshotRepository
from app.repositories.polymarket_client import PolymarketClient, UpstreamFetchError
from app.schemas.market_data import (
    MarketEvent,
    MarketOption,
    PriceSource,
    has_participation,
)
from app.services.market_data_service import MarketDataService

_FETCHED_AT = datetime(2026, 7, 6, tzinfo=timezone.utc)


# ---------------- 参与谓词三态 ----------------


def test_has_participation_missing_is_false():
    # 未设置 traders（缺省 None）→ 无参与数据
    option = MarketOption(outcome="Yes")
    assert has_participation(option) is False


def test_has_participation_explicit_null_is_false():
    option = MarketOption(outcome="Yes", traders=None)
    assert has_participation(option) is False


def test_has_participation_zero_is_true():
    # 值为 0 是有效 0，正常参与，不触发退化
    option = MarketOption(outcome="Yes", traders=0)
    assert has_participation(option) is True


# ---------------- 客户端：归一映射 / 价源 / 粒度 ----------------


def _binary_gamma_event() -> dict:
    return {
        "slug": "game-x",
        "title": "Game X",
        "category": "Sports",
        "commentCount": 5,
        "markets": [
            {
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.4", "0.6"]',
                "clobTokenIds": '["t1", "t2"]',
                "volume": "1000",
                "liquidity": "500",
                "volume24hr": "100",
                "numTraders": "7",
            }
        ],
    }


def _multi_outcome_gamma_event() -> dict:
    return {
        "slug": "winner",
        "title": "Who wins",
        "markets": [
            {
                "outcomes": '["A", "B", "C"]',
                "outcomePrices": '["0.5", "0.3", "0.2"]',
                "clobTokenIds": '["a", "b", "c"]',
                "volume": "2000",
                "liquidity": "900",
            }
        ],
    }


def _client_with_handler(handler, **kwargs) -> PolymarketClient:
    transport = httpx.MockTransport(handler)
    return PolymarketClient(
        http_client=httpx.Client(transport=transport),
        sleep=lambda _delay: None,
        **kwargs,
    )


def test_normalize_binary_event_uses_clob_price():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/midpoint"):
            return httpx.Response(200, json={"mid": "0.55"})
        return httpx.Response(200, json=[_binary_gamma_event()])

    client = _client_with_handler(handler, detail_use_midpoint=True)
    event = client.fetch_event_by_slug("game-x")

    assert event.slug == "game-x"
    assert event.comment_count == 5
    assert len(event.options) == 2
    yes = event.options[0]
    assert yes.price == 0.55
    assert yes.price_source is PriceSource.CLOB_MIDPOINT
    # 二元市场 volume 直接作选项级
    assert yes.volume == 1000.0
    assert yes.traders == 7


def test_price_falls_back_to_outcome_prices_when_clob_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/midpoint"):
            return httpx.Response(404)
        return httpx.Response(200, json=[_binary_gamma_event()])

    client = _client_with_handler(handler, detail_use_midpoint=True)
    event = client.fetch_event_by_slug("game-x")

    yes = event.options[0]
    assert yes.price == 0.4
    assert yes.price_source is PriceSource.OUTCOME_PRICES_FALLBACK


def test_multi_outcome_marks_volume_missing_with_note():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/midpoint"):
            return httpx.Response(200, json={"mid": "0.5"})
        return httpx.Response(200, json=[_multi_outcome_gamma_event()])

    client = _client_with_handler(handler, detail_use_midpoint=True)
    event = client.fetch_event_by_slug("winner")

    assert len(event.options) == 3
    for option in event.options:
        assert option.volume is None
        assert option.liquidity is None
        assert option.degraded_note is not None


def test_list_path_uses_outcome_prices_without_clob_calls():
    # 列表路径只走 1 次 Gamma /events，价格用内联 outcomePrices，不逐 outcome 打 CLOB。
    state = {"gamma": 0, "midpoint": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/midpoint"):
            state["midpoint"] += 1
            return httpx.Response(200, json={"mid": "0.99"})
        state["gamma"] += 1
        return httpx.Response(200, json=[_binary_gamma_event()])

    client = _client_with_handler(handler)
    events = client.fetch_popular_events(limit=5)

    assert state["gamma"] == 1
    assert state["midpoint"] == 0  # 列表路径不外呼 CLOB
    yes = events[0].options[0]
    assert yes.price == 0.4  # 来自 Gamma outcomePrices
    assert yes.price_source is PriceSource.OUTCOME_PRICES_FALLBACK


# ---------------- 客户端：退避重试 ----------------


def test_grouped_binary_markets_collapse_to_one_option_per_group():
    # 世界杯冠军式事件：多个「某队夺冠 Yes/No」子市场（带 groupItemTitle）折叠成
    # 「一支队 = 一个选项」，名称取组标题、概率取 Yes 侧，且不逐 outcome 打 CLOB。
    event_payload = {
        "slug": "world-cup-winner",
        "title": "World Cup Winner",
        "markets": [
            {
                "groupItemTitle": "France",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.33", "0.67"]',
                "clobTokenIds": '["f-yes", "f-no"]',
                "volume": "500",
                "numTraders": "12",
            },
            {
                "groupItemTitle": "Spain",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.13", "0.87"]',
                "clobTokenIds": '["s-yes", "s-no"]',
                "volume": "300",
                "numTraders": "8",
            },
        ],
    }
    state = {"midpoint": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/midpoint"):
            state["midpoint"] += 1
            return httpx.Response(200, json={"mid": "0.99"})
        return httpx.Response(200, json=[event_payload])

    client = _client_with_handler(handler)
    events = client.fetch_popular_events(limit=5)

    assert state["midpoint"] == 0  # 列表路径不外呼 CLOB
    event = events[0]
    assert [option.outcome for option in event.options] == ["France", "Spain"]
    france = event.options[0]
    assert france.price == 0.33  # Yes 侧概率
    assert france.price_source is PriceSource.OUTCOME_PRICES_FALLBACK
    assert france.volume == 500.0  # market 级量纲作候选项级，不重复计
    assert france.traders == 12
    assert france.degraded_note is None


def test_retry_then_success():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/events"):
            state["calls"] += 1
            if state["calls"] < 3:
                return httpx.Response(429)
            return httpx.Response(200, json=[_binary_gamma_event()])
        return httpx.Response(200, json={"mid": "0.5"})

    client = _client_with_handler(handler, retry_max_attempts=5)
    event = client.fetch_event_by_slug("game-x")
    assert event.slug == "game-x"
    assert state["calls"] == 3


def test_retry_exhausts_raises_upstream_fetch_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    client = _client_with_handler(handler, retry_max_attempts=3)
    with pytest.raises(UpstreamFetchError):
        client.fetch_event_by_slug("game-x")


def test_world_cup_filter_by_keyword():
    events = [
        {"slug": "wc-final", "title": "World Cup Final", "markets": []},
        {"slug": "election", "title": "Election 2026", "markets": []},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=events)

    client = _client_with_handler(handler)
    matched = client.fetch_world_cup_events(limit=10)
    assert [event.slug for event in matched] == ["wc-final"]


def test_world_cup_query_uses_tag_slug():
    # 世界杯默认列表按 FIFA tag 服务端拉取（等价 /sports/world-cup），而非拉任意 active。
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["tag_slug"] = request.url.params.get("tag_slug")
        captured["order"] = request.url.params.get("order")
        return httpx.Response(
            200, json=[{"slug": "wc-final", "title": "World Cup Final", "markets": []}]
        )

    client = _client_with_handler(handler)
    matched = client.fetch_world_cup_events(limit=10)

    assert captured["tag_slug"] == settings.world_cup_tag_slug
    assert captured["order"] == "volume"
    assert [event.slug for event in matched] == ["wc-final"]


# ---------------- 缓存：分层 TTL ----------------


class RecordingRedis:
    """记录每个 key 的 TTL，用于断言分层 TTL。"""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        self.ttls[key] = ex
        return True

    def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture
def recording_redis(monkeypatch):
    fake = RecordingRedis()
    monkeypatch.setattr(cache_module, "redis_client", fake)
    return fake


def _sample_event(slug: str = "game-x") -> MarketEvent:
    return MarketEvent(
        slug=slug,
        title="Game X",
        comment_count=3,
        options=[
            MarketOption(
                outcome="Yes",
                price=0.6,
                price_source=PriceSource.CLOB_MIDPOINT,
                volume=100.0,
                liquidity=50.0,
                volume24hr=12.0,
                traders=5,
                one_day_price_change=0.03,
                one_week_price_change=-0.02,
                best_bid=0.59,
                best_ask=0.61,
                spread=0.02,
                volume1wk=70.0,
                volume1mo=300.0,
                competitive=0.88,
            )
        ],
        data_snapshot_at="2026-07-06T00:00:00+00:00",
    )


def test_cache_layers_use_distinct_ttls(recording_redis):
    repo = MarketDataCacheRepository()
    repo.set_event(_sample_event())

    assert recording_redis.ttls["market:meta:game-x"] == settings.market_metadata_ttl
    assert recording_redis.ttls["market:price:game-x"] == settings.market_price_ttl
    assert (
        recording_redis.ttls["market:fallback:game-x"] == settings.market_fallback_ttl
    )


def test_cache_fresh_hit_reconstructs_event(recording_redis):
    repo = MarketDataCacheRepository()
    repo.set_event(_sample_event())

    fresh = repo.get_fresh_event("game-x")
    assert fresh is not None
    assert fresh.options[0].price == 0.6
    assert fresh.options[0].price_source is PriceSource.CLOB_MIDPOINT
    assert fresh.options[0].volume == 100.0
    assert fresh.options[0].liquidity == 50.0
    assert fresh.options[0].volume24hr == 12.0
    assert fresh.options[0].one_day_price_change == 0.03
    assert fresh.options[0].one_week_price_change == -0.02
    assert fresh.options[0].best_bid == 0.59
    assert fresh.options[0].best_ask == 0.61
    assert fresh.options[0].spread == 0.02
    assert fresh.options[0].volume1wk == 70.0
    assert fresh.options[0].volume1mo == 300.0
    assert fresh.options[0].competitive == 0.88


def test_cache_miss_when_price_layer_absent(recording_redis):
    repo = MarketDataCacheRepository()
    repo.set_event(_sample_event())
    # 价格层过期/缺失 → 未命中，触发回源
    recording_redis.delete("market:price:game-x")
    assert repo.get_fresh_event("game-x") is None
    # 但 fallback 快照仍在
    assert repo.get_fallback_event("game-x") is not None


# ---------------- service：降级链 ----------------


class StubClient:
    def __init__(self, event: MarketEvent | None = None, fail: bool = False):
        self._event = event or _sample_event()
        self._fail = fail
        self.calls = 0

    def fetch_event_by_slug(self, slug: str) -> MarketEvent:
        self.calls += 1
        if self._fail:
            raise UpstreamFetchError("boom")
        return self._event

    def fetch_popular_events(self, limit=None):
        if self._fail:
            raise UpstreamFetchError("boom")
        return [self._event]

    def fetch_world_cup_events(self, limit=None):
        if self._fail:
            raise UpstreamFetchError("boom")
        return [self._event]


def test_service_fresh_cache_hit_skips_client(recording_redis):
    repo = MarketDataCacheRepository()
    repo.set_event(_sample_event())
    client = StubClient()
    service = MarketDataService(client, repo)

    event = service.get_event("game-x")
    assert event.slug == "game-x"
    assert client.calls == 0  # 命中缓存，不打上游


def test_service_fetches_and_writes_cache_on_miss(recording_redis):
    repo = MarketDataCacheRepository()
    client = StubClient()
    service = MarketDataService(client, repo)

    event = service.get_event("game-x")
    assert event.slug == "game-x"
    assert client.calls == 1
    # 已写入缓存
    assert repo.get_fresh_event("game-x") is not None


def test_service_upstream_fail_falls_back_to_snapshot(recording_redis):
    repo = MarketDataCacheRepository()
    repo.set_event(_sample_event())
    # 让 fresh 层失效，仅保留 fallback
    recording_redis.delete("market:price:game-x")
    client = StubClient(fail=True)
    service = MarketDataService(client, repo)

    event = service.get_event("game-x")
    assert event.slug == "game-x"  # 回退 fallback 快照


def test_service_upstream_fail_no_cache_raises(recording_redis):
    repo = MarketDataCacheRepository()
    client = StubClient(fail=True)
    service = MarketDataService(client, repo)

    with pytest.raises(UpstreamUnavailableException):
        service.get_event("missing")


def test_prefetch_writes_lists_to_cache(recording_redis):
    repo = MarketDataCacheRepository()
    client = StubClient()
    service = MarketDataService(client, repo)

    service.prefetch_default_lists()
    assert repo.get_fresh_list("popular") is not None
    assert repo.get_fresh_list("world_cup") is not None


def test_set_list_also_backfills_event_cache(recording_redis):
    repo = MarketDataCacheRepository()

    repo.set_list("popular", [_sample_event("game-x")])

    assert repo.get_fresh_list("popular") is not None
    assert repo.get_fresh_event("game-x") is not None


class _NoServingFetchClient(StubClient):
    """serving 路径若同步回源即失败，用于断言请求路径不打上游。"""

    def fetch_popular_events(self, limit=None):
        raise AssertionError("serving path must not fetch upstream")

    def fetch_world_cup_events(self, limit=None):
        raise AssertionError("serving path must not fetch upstream")


def test_service_list_request_path_never_fetches_upstream(recording_redis):
    # 冷缓存下请求路径（force_refresh=False）不打上游，返回空，交由后台预取补齐。
    repo = MarketDataCacheRepository()
    service = MarketDataService(_NoServingFetchClient(), repo)

    assert service.get_popular_events() == []


def test_service_list_request_path_serves_fallback_snapshot(recording_redis):
    # fresh 层缺失但 fallback 快照在：请求路径回退快照，仍不打上游。
    repo = MarketDataCacheRepository()
    repo.set_list("popular", [_sample_event("a")])
    recording_redis.delete("market:list:popular")  # 让 fresh 失效，仅留 fallback
    service = MarketDataService(_NoServingFetchClient(), repo)

    events = service.get_popular_events()
    assert [event.slug for event in events] == ["a"]


# ---------------- DB 快照持久层 ----------------


def test_snapshot_repository_round_trip(db_session):
    repo = MarketSnapshotRepository(db_session)
    repo.save_list_snapshot(
        "popular", [_sample_event("a"), _sample_event("b")], _FETCHED_AT
    )

    got = repo.get_list("popular")
    assert [event.slug for event in got] == ["a", "b"]  # 保留原序
    assert repo.get_event("a").slug == "a"
    assert repo.get_event("missing") is None


def test_snapshot_repository_upsert_overwrites_latest(db_session):
    repo = MarketSnapshotRepository(db_session)
    repo.save_list_snapshot("popular", [_sample_event("a")], _FETCHED_AT)
    # 再摄取覆盖为最新（按 name/slug upsert，不追加历史行）
    repo.save_list_snapshot("popular", [_sample_event("c")], _FETCHED_AT)

    assert [event.slug for event in repo.get_list("popular")] == ["c"]


def test_service_serving_reads_db_when_redis_cold(db_session, recording_redis):
    # 模拟重启后 Redis 冷、DB 有快照：serving 读 DB 并回填 Redis，且不打上游。
    snapshots = MarketSnapshotRepository(db_session)
    snapshots.save_list_snapshot("popular", [_sample_event("a")], _FETCHED_AT)
    service = MarketDataService(
        _NoServingFetchClient(), MarketDataCacheRepository(), snapshots
    )

    events = service.get_popular_events()
    assert [event.slug for event in events] == ["a"]
    # 已回填 Redis 热缓存
    assert recording_redis.store.get("market:list:popular") is not None


def test_service_single_event_reads_db_when_redis_cold(db_session, recording_redis):
    snapshots = MarketSnapshotRepository(db_session)
    snapshots.save_list_snapshot("popular", [_sample_event("game-x")], _FETCHED_AT)
    # 单事件 serving：Redis 冷 → 读 DB 命中，不回源
    service = MarketDataService(
        StubClient(fail=True), MarketDataCacheRepository(), snapshots
    )

    event = service.get_event("game-x")
    assert event.slug == "game-x"


def test_service_ingest_writes_redis_and_db(db_session, recording_redis):
    # 摄取路径（force_refresh）同时写 Redis + DB 持久快照。
    snapshots = MarketSnapshotRepository(db_session)
    service = MarketDataService(StubClient(), MarketDataCacheRepository(), snapshots)

    service.prefetch_default_lists()

    assert snapshots.get_list("popular") is not None
    assert snapshots.get_event("game-x") is not None


def test_refresh_claim_is_throttled_by_redis_lock(recording_redis):
    repo = MarketDataCacheRepository()

    assert repo.claim_refresh("list:popular") is True
    assert repo.claim_refresh("list:popular") is False
    assert (
        recording_redis.ttls["market:refresh-lock:list:popular"]
        == settings.market_refresh_throttle_seconds
    )


def test_service_maybe_refresh_list_is_throttled(recording_redis):
    repo = MarketDataCacheRepository()
    client = StubClient()
    service = MarketDataService(client, repo)

    assert service.maybe_refresh_list("popular") is True
    assert service.maybe_refresh_list("popular") is False


def test_service_single_event_fetch_persists_db_snapshot(db_session, recording_redis):
    snapshots = MarketSnapshotRepository(db_session)
    service = MarketDataService(StubClient(), MarketDataCacheRepository(), snapshots)

    event = service.get_event("game-x")

    assert event.slug == "game-x"
    assert snapshots.get_event("game-x").slug == "game-x"
