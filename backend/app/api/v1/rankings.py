"""多事件排行对外分析路由（analysis-ranking-api）。

对当前 Tab 默认列表聚合泡沫/冷门/合理三榜，每榜 TopN 截取、每项保留事件归属。
排行走预取缓存，不接入实时限流（design D5/D6）。
"""

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.schemas.analysis import EventCategory, RankingBoards
from app.schemas.response import ApiResponse, success_response
from app.services.analysis_service import AnalysisService, build_analysis_service

router = APIRouter(prefix="/rankings", tags=["rankings"])


def get_analysis_service() -> AnalysisService:
    return build_analysis_service()


@router.get("", response_model=ApiResponse[RankingBoards])
def get_rankings(
    category: EventCategory = Query(EventCategory.HOT),
    top_n: int = Query(settings.ranking_top_n, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis_service),
):
    result = service.get_rankings(category, top_n)
    return success_response(result)
