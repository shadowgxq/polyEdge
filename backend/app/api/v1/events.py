"""事件类对外分析路由（analysis-event-api）。

默认列表 / 单事件明细 / slug 解析 / 名称搜索四个端点；只做参数声明、调用组合
service、`success_response` 返回，不写业务规则（layer-definition.md）。实时路径
（明细刷新 / slug 解析拉取 / 名称搜索）接入服务端限流依赖（design D6）。
"""

from fastapi import APIRouter, Depends, Path, Query, Request

from app.core.config import settings
from app.schemas.analysis import (
    EventCategory,
    EventDetail,
    EventListResponse,
    EventSearchResult,
    ResolveEventRequest,
)
from app.schemas.response import ApiResponse, success_response
from app.services.analysis_service import AnalysisService, build_analysis_service
from app.services.rate_limit_service import RateLimitService, build_rate_limit_service

router = APIRouter(prefix="/events", tags=["events"])


def get_analysis_service() -> AnalysisService:
    return build_analysis_service()


def get_rate_limit_service() -> RateLimitService:
    return build_rate_limit_service()


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


@router.get("", response_model=ApiResponse[EventListResponse])
def list_events(
    category: EventCategory = Query(EventCategory.HOT),
    page: int = Query(1, ge=1),
    page_size: int = Query(
        settings.event_list_page_size,
        ge=1,
        le=settings.event_list_page_size,
    ),
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.get_event_list(category, page, page_size)
    return success_response(result)


@router.get(
    "/search",
    response_model=ApiResponse[EventSearchResult],
    dependencies=[Depends(enforce_realtime_rate_limit)],
)
def search_events(
    q: str = Query(..., min_length=1),
    limit: int = Query(settings.event_search_limit, ge=1, le=50),
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.search_events(q, limit)
    return success_response(result)


@router.post(
    "/resolve",
    response_model=ApiResponse[EventDetail],
    dependencies=[Depends(enforce_realtime_rate_limit)],
)
def resolve_event(
    payload: ResolveEventRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.resolve_event(payload.input)
    return success_response(result)


@router.get(
    "/{slug}",
    response_model=ApiResponse[EventDetail],
    dependencies=[Depends(enforce_realtime_rate_limit)],
)
def get_event_detail(
    slug: str = Path(..., min_length=1),
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.get_event_detail(slug, force_refresh=True)
    return success_response(result)
