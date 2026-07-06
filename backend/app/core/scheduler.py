"""进程内轻量定时调度（core/scheduler）。

用后台守护线程按固定间隔调用回调，异常不中断循环。用于市场数据定时预取
（design D7：应用 lifespan 内定时任务，避免引入重型第三方调度依赖）。
"""

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class IntervalScheduler:
    """固定间隔调度器：`start()` 挂载后台线程，`stop()` 优雅停止。"""

    def __init__(
        self,
        interval_seconds: float,
        task: Callable[[], None],
        *,
        run_immediately: bool = True,
        name: str = "interval-scheduler",
    ):
        self._interval_seconds = interval_seconds
        self._task = task
        self._run_immediately = run_immediately
        self._name = name
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()
        logger.info(
            "scheduler started name=%s interval=%ss", self._name, self._interval_seconds
        )

    def _run(self) -> None:
        if self._run_immediately:
            self._safe_task()
        # wait(interval) 返回 True 表示收到停止信号，否则超时后再跑一轮。
        while not self._stop_event.wait(self._interval_seconds):
            self._safe_task()

    def _safe_task(self) -> None:
        try:
            self._task()
        except Exception:  # noqa: BLE001 - 调度回调异常不得中断调度循环
            logger.exception("scheduled task failed name=%s", self._name)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("scheduler stopped name=%s", self._name)
