"""market-data 数据接入测试：归一映射、价源回退、粒度兜底、参与谓词三态、
分层 TTL、退避重试、失败回退缓存 / 无缓存报错、预取入缓存。"""

import httpx
import pytest

import app.repositories.market_data_cache_repository as cache_module
from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableException
from app.repositories.market_data_cache_repository import MarketDataCacheRepository
from app.repositories.polymarket_client import PolymarketClient, UpstreamFetchError
from app.schemas.market_data import (
    MarketEvent,
    MarketOption,
    PriceSource,
    has_participation,
)
from app.services.market_data_service import MarketDataService


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

    client = _client_with_handler(handler)
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

    client = _client_with_handler(handler)
    event = client.fetch_event_by_slug("game-x")

    yes = event.options[0]
    assert yes.price == 0.4
    assert yes.price_source is PriceSource.OUTCOME_PRICES_FALLBACK


def test_multi_outcome_marks_volume_missing_with_note():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/midpoint"):
            return httpx.Response(200, json={"mid": "0.5"})
        return httpx.Response(200, json=[_multi_outcome_gamma_event()])

    client = _client_with_handler(handler)
    event = client.fetch_event_by_slug("winner")

    assert len(event.options) == 3
    for option in event.options:
        assert option.volume is None
        assert option.liquidity is None
        assert option.degraded_note is not None


# ---------------- 客户端：退避重试 ----------------


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


# ---------------- 缓存：分层 TTL ----------------


class RecordingRedis:
    """记录每个 key 的 TTL，用于断言分层 TTL。"""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        self.ttls[key] = ex

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
                traders=5,
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
