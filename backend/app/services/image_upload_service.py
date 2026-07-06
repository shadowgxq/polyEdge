"""图片上传落盘服务。

用于分享海报：前端将生成后的图片 Blob 作为请求体上传，服务端校验 MIME / 大小后
保存到本地静态目录，并返回可访问路径。此服务不接收任意文件名，避免路径穿越和覆盖。
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import ImageUploadInvalidException


_EXTENSION_BY_CONTENT_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class StoredImage:
    """落盘后的图片元信息。"""

    path: str
    content_type: str
    size: int


def _normalize_content_type(content_type: str | None) -> str:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type not in settings.image_upload_allowed_types:
        raise ImageUploadInvalidException("Unsupported image content type")
    if media_type not in _EXTENSION_BY_CONTENT_TYPE:
        raise ImageUploadInvalidException("Unsupported image content type")
    return media_type


def _validate_content(content: bytes) -> None:
    if not content:
        raise ImageUploadInvalidException("Uploaded image is empty")
    if len(content) > settings.image_upload_max_bytes:
        raise ImageUploadInvalidException("Uploaded image exceeds size limit")


def _storage_root() -> Path:
    root = Path(settings.upload_storage_dir)
    if not root.is_absolute():
        root = Path.cwd() / root
    return root


def store_uploaded_image(content: bytes, content_type: str | None) -> StoredImage:
    """校验并保存上传图片，返回静态访问 path。"""

    media_type = _normalize_content_type(content_type)
    _validate_content(content)

    image_dir = _storage_root() / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid4().hex}{_EXTENSION_BY_CONTENT_TYPE[media_type]}"
    file_path = image_dir / file_name
    file_path.write_bytes(content)

    return StoredImage(
        path=f"/uploads/images/{file_name}",
        content_type=media_type,
        size=len(content),
    )
