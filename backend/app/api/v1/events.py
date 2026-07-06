"""事件类对外分析路由（analysis-event-api）。

默认列表 / 单事件明细 / slug 解析 / 名称搜索四个端点；只做参数声明、调用组合
service、`success_response` 返回，不写业务规则（layer-definition.md）。实时路径
（明细刷新 / slug 解析拉取 / 名称搜索）接入服务端限流依赖（design D6）。
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.session import SessionLocal, get_db
from app.schemas.analysis import (
    EventCategory,
    EventDetail,
    EventListResponse,
    EventSearchResult,
    ResolveEventRequest,
)
from app.schemas.response import ApiResponse, success_response
from app.services.analysis_service import AnalysisService, build_analysis_service
from app.services.market_data_service import build_market_data_service
from app.services.rate_limit_service import RateLimitService, build_rate_limit_service

router = APIRouter(prefix="/events", tags=["events"])

_POPULAR_LIST = "popular"
_WORLD_CUP_LIST = "world_cup"


def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    return build_analysis_service(db)


def get_rate_limit_service() -> RateLimitService:
    return build_rate_limit_service()


class MarketRefreshScheduler:
    """请求触发型刷新投递器；实际限频在 service 的 Redis refresh lock 中完成。"""

    def schedule_event(self, background_tasks: BackgroundTasks, slug: str) -> None:
        background_tasks.add_task(_refresh_event, slug)

    def schedule_list(self, background_tasks: BackgroundTasks, name: str) -> None:
        background_tasks.add_task(_refresh_list, name)


def get_market_refresh_scheduler() -> MarketRefreshScheduler:
    return MarketRefreshScheduler()


def _client_identity(request: Request) -> str:
    """限流标识：优先匿名会话 id（无登录），退化为客户端 IP（design D6）。"""
    session_id = request.headers.get("X-Session-Id")
    if session_id:
        return f"session:{session_id}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def enforce_realtime_rate_limit(
    request: Request,
    service: RateLimitService = Depends(get_rate_limit_service),
) -> None:
    """实时路径限流依赖：超阈值抛 429，Redis 故障 fail-open 放行。"""
    service.enforce(_client_identity(request))


def _refresh_event(slug: str) -> None:
    """响应后后台刷新单事件；独立 DB 会话，避免复用已关闭的请求 session。"""
    with SessionLocal() as db:
        build_market_data_service(db).maybe_refresh_event(slug)


def _refresh_list(name: str) -> None:
    """响应后后台刷新默认列表；同名列表由 Redis 刷新锁限频。"""
    with SessionLocal() as db:
        build_market_data_service(db).maybe_refresh_list(name)


def _list_name(category: EventCategory) -> str:
    return _WORLD_CUP_LIST if category is EventCategory.WORLD_CUP else _POPULAR_LIST


@router.get("", response_model=ApiResponse[EventListResponse])
def list_events(
    background_tasks: BackgroundTasks,
    category: EventCategory = Query(EventCategory.HOT),
    page: int = Query(1, ge=1),
    page_size: int = Query(
        settings.event_list_page_size,
        ge=1,
        le=settings.event_list_page_size,
    ),
    service: AnalysisService = Depends(get_analysis_service),
    refresh_scheduler: MarketRefreshScheduler = Depends(get_market_refresh_scheduler),
):
    result = service.get_event_list(category, page, page_size)
    refresh_scheduler.schedule_list(background_tasks, _list_name(category))
    return success_response(result)


@router.get(
    "/search",
    response_model=ApiResponse[EventSearchResult],
    dependencies=[Depends(enforce_realtime_rate_limit)],
)
def search_events(
    background_tasks: BackgroundTasks,
    q: str = Query(..., min_length=1),
    limit: int = Query(settings.event_search_limit, ge=1, le=50),
    service: AnalysisService = Depends(get_analysis_service),
    refresh_scheduler: MarketRefreshScheduler = Depends(get_market_refresh_scheduler),
):
    result = service.search_events(q, limit)
    refresh_scheduler.schedule_list(background_tasks, _POPULAR_LIST)
    refresh_scheduler.schedule_list(background_tasks, _WORLD_CUP_LIST)
    return success_response(result)


@router.post(
    "/resolve",
    response_model=ApiResponse[EventDetail],
    dependencies=[Depends(enforce_realtime_rate_limit)],
)
def resolve_event(
    background_tasks: BackgroundTasks,
    payload: ResolveEventRequest,
    service: AnalysisService = Depends(get_analysis_service),
    refresh_scheduler: MarketRefreshScheduler = Depends(get_market_refresh_scheduler),
):
    result = service.resolve_event(payload.input)
    refresh_scheduler.schedule_event(background_tasks, result.slug)
    return success_response(result)


@router.get(
    "/{slug}",
    response_model=ApiResponse[EventDetail],
    dependencies=[Depends(enforce_realtime_rate_limit)],
)
def get_event_detail(
    background_tasks: BackgroundTasks,
    slug: str = Path(..., min_length=1),
    service: AnalysisService = Depends(get_analysis_service),
    refresh_scheduler: MarketRefreshScheduler = Depends(get_market_refresh_scheduler),
):
    result = service.get_event_detail(slug)
    refresh_scheduler.schedule_event(background_tasks, slug)
    return success_response(result)
