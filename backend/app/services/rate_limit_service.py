"""实时路径服务端限流（analysis-api、design D6、data-source §5）。

对绕过预取缓存的实时请求（名称搜索、slug 解析拉取、单事件明细刷新）按 IP / 会话
在 Redis 固定窗口计数，超阈值抛 `RateLimitExceededException`（HTTP 429）。计数经
`core/redis_client` 的 `@redis_safe` 封装，Redis 故障时 `default=0`（fail-open，不误伤、
不阻断主流程，呼应 infrastructure.md 限流降级方向）。默认列表 / 排行走预取缓存不接入。
"""

import time

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException
from app.core.redis_client import redis_client, redis_safe

_RATE_LIMIT_PREFIX = "ratelimit:realtime:"


@redis_safe(default=0)
def _incr_window(key: str, window_seconds: int) -> int:
    """对固定窗口 key 计数 +1；首次计数时设置窗口过期。失败降级返回 0（fail-open）。"""
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window_seconds)
    return count


class RateLimitService:
    """按标识（IP / 会话）的 Redis 固定窗口限流。"""

    def __init__(self, window_seconds: int, max_requests: int):
        self._window_seconds = window_seconds
        self._max_requests = max_requests

    def enforce(self, identity: str) -> None:
        """对某标识在当前窗口内的实时请求计数并校验阈值；超限抛业务异常。

        Redis 计数故障时 `_incr_window` 返回 0，count 恒 < 阈值 → 不拦截（fail-open）。
        """
        bucket = int(time.time()) // self._window_seconds
        key = f"{_RATE_LIMIT_PREFIX}{identity}:{bucket}"
        count = _incr_window(key, self._window_seconds)
        if count > self._max_requests:
            raise RateLimitExceededException()


def build_rate_limit_service() -> RateLimitService:
    """按配置装配实时路径限流 service。"""
    return RateLimitService(
        window_seconds=settings.realtime_rate_limit_window,
        max_requests=settings.realtime_rate_limit_max,
    )
