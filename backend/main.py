from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.image_proxy import router as image_proxy_router
from app.api.v1.rankings import router as rankings_router
from app.core.config import settings
from app.core.exception_handlers import (
    business_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import BusinessException

from app.core.logging import setup_logging
from app.core.middlewares import request_log_middleware
from app.core.scheduler import IntervalScheduler
from app.services.market_data_service import build_market_data_service

setup_logging()


def _build_prefetch_scheduler() -> IntervalScheduler:
    """装配市场数据定时预取调度器（热门 + 世界杯默认列表批量预取入缓存）。"""
    service = build_market_data_service()
    return IntervalScheduler(
        interval_seconds=settings.market_prefetch_interval_seconds,
        task=service.prefetch_default_lists,
        run_immediately=True,
        name="market-prefetch",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler: IntervalScheduler | None = None
    if settings.market_prefetch_enabled:
        scheduler = _build_prefetch_scheduler()
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.stop()


app = FastAPI(title="Backend Agent Template API", lifespan=lifespan)

app.middleware("http")(request_log_middleware)

# 注册统一异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(image_proxy_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(rankings_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
