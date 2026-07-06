"""多事件排行对外分析路由（analysis-ranking-api）。

对当前 Tab 默认列表聚合泡沫/冷门/合理三榜，每榜 TopN 截取、每项保留事件归属。
排行走预取缓存，不接入实时限流（design D5/D6）。
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.session import SessionLocal, get_db
from app.schemas.analysis import EventCategory, RankingBoards
from app.schemas.response import ApiResponse, success_response
from app.services.analysis_service import AnalysisService, build_analysis_service
from app.services.market_data_service import build_market_data_service

router = APIRouter(prefix="/rankings", tags=["rankings"])

_POPULAR_LIST = "popular"
_WORLD_CUP_LIST = "world_cup"


def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    return build_analysis_service(db)


class MarketRefreshScheduler:
    """请求触发型刷新投递器；实际限频在 service 的 Redis refresh lock 中完成。"""

    def schedule_list(self, background_tasks: BackgroundTasks, name: str) -> None:
        background_tasks.add_task(_refresh_list, name)


def get_market_refresh_scheduler() -> MarketRefreshScheduler:
    return MarketRefreshScheduler()


def _refresh_list(name: str) -> None:
    """响应后后台刷新默认列表；同名列表由 Redis 刷新锁限频。"""
    with SessionLocal() as db:
        build_market_data_service(db).maybe_refresh_list(name)


def _list_name(category: EventCategory) -> str:
    return _WORLD_CUP_LIST if category is EventCategory.WORLD_CUP else _POPULAR_LIST


@router.get("", response_model=ApiResponse[RankingBoards])
def get_rankings(
    background_tasks: BackgroundTasks,
    category: EventCategory = Query(EventCategory.HOT),
    top_n: int = Query(settings.ranking_top_n, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis_service),
    refresh_scheduler: MarketRefreshScheduler = Depends(get_market_refresh_scheduler),
):
    result = service.get_rankings(category, top_n)
    refresh_scheduler.schedule_list(background_tasks, _list_name(category))
    return success_response(result)
