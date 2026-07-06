"""Redis 分层 TTL 缓存仓储（market-data-cache）。

经 `core/redis_client` 的共享客户端读写（不直连 Redis），所有操作 `redis_safe` 容错降级。
分层 key + 分层 TTL：元数据/列表分钟级、价格/赔率秒~十秒级，两层独立失效
（data-source §4、PRD §5.3）。另存一份长 TTL fallback 快照，供上游失败时回退（含过期）。

- fresh 读路径（get_fresh_*）：仅当 meta 与 price 两层均命中且未过期才返回，用于「命中
  缓存直接返回」；任一层缺失视为未命中，触发回源。
- fallback 读路径（get_fallback_*）：读长 TTL 快照，供退避耗尽后的降级回退。
"""

import json
import logging

from app.core.config import settings
from app.core.redis_client import redis_client, redis_safe
from app.schemas.market_data import MarketEvent, MarketOption, PriceSource

logger = logging.getLogger(__name__)

_META_PREFIX = "market:meta:"
_PRICE_PREFIX = "market:price:"
_FALLBACK_PREFIX = "market:fallback:"
_LIST_PREFIX = "market:list:"
_LIST_FALLBACK_PREFIX = "market:list:fallback:"


@redis_safe(default=None)
def _get_raw(key: str) -> str | None:
    return redis_client.get(key)


@redis_safe()
def _set_raw(key: str, value: str, ttl: int) -> None:
    redis_client.set(key, value, ex=ttl)


def _dumps(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _loads(value: str | None) -> dict | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class MarketDataCacheRepository:
    """归一化事件/列表的分层缓存读写。"""

    # ---------------- 单事件：分层写 ----------------

    def set_event(self, event: MarketEvent) -> None:
        """分层写入：元数据（长 TTL）+ 价格（短 TTL）+ fallback 全量快照（长 TTL）。"""
        slug = event.slug
        snapshot_iso = event.data_snapshot_at.isoformat()
        meta_payload = {
            "slug": slug,
            "title": event.title,
            "category": event.category,
            "comment_count": event.comment_count,
            "data_snapshot_at": snapshot_iso,
            "options": [
                {
                    "outcome": option.outcome,
                    "volume": option.volume,
                    "liquidity": option.liquidity,
                    "volume24hr": option.volume24hr,
                    "traders": option.traders,
                    "degraded_note": option.degraded_note,
                }
                for option in event.options
            ],
        }
        price_payload = {
            "data_snapshot_at": snapshot_iso,
            "prices": {
                option.outcome: {
                    "price": option.price,
                    "price_source": option.price_source.value,
                }
                for option in event.options
            },
        }
        _set_raw(
            _META_PREFIX + slug, _dumps(meta_payload), settings.market_metadata_ttl
        )
        _set_raw(_PRICE_PREFIX + slug, _dumps(price_payload), settings.market_price_ttl)
        _set_raw(
            _FALLBACK_PREFIX + slug,
            _dumps(event.model_dump(mode="json")),
            settings.market_fallback_ttl,
        )

    def get_fresh_event(self, slug: str) -> MarketEvent | None:
        """两层均命中且未过期时重建事件；任一层缺失 → None（回源）。"""
        meta = _loads(_get_raw(_META_PREFIX + slug))
        price = _loads(_get_raw(_PRICE_PREFIX + slug))
        if meta is None or price is None:
            return None
        return _merge_event(meta, price)

    def get_fallback_event(self, slug: str) -> MarketEvent | None:
        """读长 TTL fallback 快照（可能已过期口径），带其原始 data_snapshot_at。"""
        payload = _loads(_get_raw(_FALLBACK_PREFIX + slug))
        if payload is None:
            return None
        return MarketEvent.model_validate(payload)

    # ---------------- 列表：整体写 ----------------

    def set_list(self, name: str, events: list[MarketEvent]) -> None:
        """列表整体写入：fresh（元数据 TTL）+ fallback（长 TTL）。"""
        payload = {"events": [event.model_dump(mode="json") for event in events]}
        serialized = _dumps(payload)
        _set_raw(_LIST_PREFIX + name, serialized, settings.market_metadata_ttl)
        _set_raw(_LIST_FALLBACK_PREFIX + name, serialized, settings.market_fallback_ttl)

    def get_fresh_list(self, name: str) -> list[MarketEvent] | None:
        return _load_list(_get_raw(_LIST_PREFIX + name))

    def get_fallback_list(self, name: str) -> list[MarketEvent] | None:
        return _load_list(_get_raw(_LIST_FALLBACK_PREFIX + name))


def _merge_event(meta: dict, price: dict) -> MarketEvent:
    """合并元数据层与价格层为完整事件；快照时间取价格层（更短 TTL，更新鲜）。"""
    prices = price.get("prices") or {}
    options: list[MarketOption] = []
    for raw_option in meta.get("options") or []:
        outcome = raw_option.get("outcome")
        price_entry = prices.get(outcome) or {}
        options.append(
            MarketOption(
                outcome=outcome,
                price=price_entry.get("price"),
                price_source=PriceSource(
                    price_entry.get("price_source", PriceSource.UNAVAILABLE.value)
                ),
                volume=raw_option.get("volume"),
                liquidity=raw_option.get("liquidity"),
                volume24hr=raw_option.get("volume24hr"),
                traders=raw_option.get("traders"),
                degraded_note=raw_option.get("degraded_note"),
            )
        )
    return MarketEvent(
        slug=meta["slug"],
        title=meta.get("title") or meta["slug"],
        category=meta.get("category"),
        comment_count=meta.get("comment_count"),
        options=options,
        data_snapshot_at=price.get("data_snapshot_at") or meta["data_snapshot_at"],
    )


def _load_list(value: str | None) -> list[MarketEvent] | None:
    payload = _loads(value)
    if payload is None:
        return None
    return [MarketEvent.model_validate(raw) for raw in payload.get("events") or []]
