"""文件上传接口。"""

from fastapi import APIRouter, Request

from app.schemas.response import ApiResponse, success_response
from app.schemas.upload import UploadedImage
from app.services.image_upload_service import store_uploaded_image

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/images", response_model=ApiResponse[UploadedImage])
async def upload_image(request: Request):
    """上传分享海报图片并返回可访问 URL。

    请求体直接为图片二进制，`Content-Type` 必须是允许的 image MIME。
    """

    content = await request.body()
    stored = store_uploaded_image(content, request.headers.get("content-type"))
    payload = UploadedImage(
        url=str(request.url_for("uploads", path=stored.path.removeprefix("/uploads/"))),
        path=stored.path,
        content_type=stored.content_type,
        size=stored.size,
    )
    return success_response(payload.model_dump())
