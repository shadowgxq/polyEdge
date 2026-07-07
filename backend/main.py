from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.image_proxy import router as image_proxy_router
from app.api.v1.rankings import router as rankings_router
from app.api.v1.uploads import router as uploads_router
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
from app.core.session import SessionLocal
from app.services.market_data_service import build_market_data_service

setup_logging()

Path(settings.upload_storage_dir).mkdir(parents=True, exist_ok=True)


def _ingest_default_lists() -> None:
    """后台摄取一轮：每 tick 开独立 DB 会话，回源默认列表并写 Redis + DB 快照。

    会话逐 tick 创建/关闭（不长驻线程），DB 快照作为 serving 的持久数据源。
    """
    with SessionLocal() as db:
        service = build_market_data_service(db)
        service.prefetch_default_lists()


def _build_prefetch_scheduler() -> IntervalScheduler:
    """装配市场数据定时摄取调度器（热门 + 世界杯默认列表批量摄取入 Redis + DB）。"""
    return IntervalScheduler(
        interval_seconds=settings.market_prefetch_interval_seconds,
        task=_ingest_default_lists,
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

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.middleware("http")(request_log_middleware)
app.mount(
    "/uploads", StaticFiles(directory=settings.upload_storage_dir), name="uploads"
)

# 注册统一异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(image_proxy_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(rankings_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
