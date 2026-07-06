"""图片代理路由：为海报出图提供同源安全图片代理。

接收目标图片 URL 查询参数，经 service 施加防 SSRF 安全约束后，
以二进制图片流（同源、非 ApiResponse 包裹）返回，供前端绘入 canvas。
"""

import io

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.services.image_proxy_service import fetch_image

router = APIRouter(prefix="/image-proxy", tags=["image-proxy"])


@router.get("")
def proxy_image(
    url: str | None = Query(default=None, description="目标 Polymarket 图片 URL"),
):
    """代理拉取目标图片并以同源二进制流返回。

    成功路径为二进制图片流（不包 ApiResponse）；校验失败 / 上游异常由
    service 抛 BusinessException 子类，经全局 handler 转统一错误响应。
    缺失 / 空 URL 亦由 service 抛业务异常，不发起任何出站请求。
    """
    image = fetch_image(url)
    return StreamingResponse(
        io.BytesIO(image.content),
        media_type=image.media_type,
    )
