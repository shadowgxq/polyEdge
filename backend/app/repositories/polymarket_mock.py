"""Polymarket Mock 客户端（可测性 / 故障注入，非生产）。

用于稳定复现「拉取失败 ± 缓存命中」「参与数据缺失退化」分支（PRD §1.4、data-source §4、
design D9）。仅当 `settings.polymarket_mock_enabled` 开启时经工厂装配，Mock 不进生产
数据路径。fault_mode 取值：

- ""（默认）        正常返回带 traders 的归一化事件
- "fail"           所有拉取抛 UpstreamFetchError（模拟上游不可用）
- "no_participation" 选项 traders=None（触发下游全事件退化）
"""

from datetime import datetime, timezone

from app.repositories.polymarket_client import UpstreamFetchError
from app.schemas.market_data import MarketEvent, MarketOption, PriceSource


class MockPolymarketClient:
    """内存 Mock，签名与 PolymarketClient 对齐（duck typing）。"""

    def __init__(self, fault_mode: str = ""):
        self._fault_mode = fault_mode

    def _guard(self) -> None:
        if self._fault_mode == "fail":
            raise UpstreamFetchError("mock fault injection: upstream unavailable")

    def _build_event(self, slug: str, title: str) -> MarketEvent:
        traders = None if self._fault_mode == "no_participation" else 120
        return MarketEvent(
            slug=slug,
            title=title,
            category="mock",
            comment_count=42,
            options=[
                MarketOption(
                    outcome="Yes",
                    price=0.62,
                    price_source=PriceSource.CLOB_MIDPOINT,
                    volume=10000.0,
                    liquidity=5000.0,
                    volume24hr=800.0,
                    traders=traders,
                ),
                MarketOption(
                    outcome="No",
                    price=0.38,
                    price_source=PriceSource.OUTCOME_PRICES_FALLBACK,
                    volume=9000.0,
                    liquidity=4800.0,
                    volume24hr=700.0,
                    traders=traders,
                ),
            ],
            data_snapshot_at=datetime.now(timezone.utc),
        )

    def fetch_event_by_slug(self, slug: str) -> MarketEvent:
        self._guard()
        return self._build_event(slug, f"Mock event {slug}")

    def fetch_popular_events(self, limit: int | None = None) -> list[MarketEvent]:
        self._guard()
        count = limit or 3
        return [
            self._build_event(f"mock-popular-{i}", f"Mock popular {i}")
            for i in range(count)
        ]

    def fetch_world_cup_events(self, limit: int | None = None) -> list[MarketEvent]:
        self._guard()
        count = limit or 2
        return [
            self._build_event(f"mock-worldcup-{i}", f"Mock world cup {i}")
            for i in range(count)
        ]
