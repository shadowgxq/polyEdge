"""上传接口响应模型。"""

from pydantic import BaseModel


class UploadedImage(BaseModel):
    """已上传图片的访问地址。"""

    url: str
    path: str
    content_type: str
    size: int
