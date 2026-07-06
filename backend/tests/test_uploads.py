"""图片上传接口测试。"""

from pathlib import Path

from app.core.config import settings

UPLOAD_IMAGES = "/api/v1/uploads/images"


def test_upload_image_success(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    body = b"\x89PNG\r\n\x1a\n-image-bytes"

    resp = client.post(
        UPLOAD_IMAGES, content=body, headers={"content-type": "image/png"}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert data["url"].startswith("http://testserver/uploads/images/")
    assert data["path"].startswith("/uploads/images/")
    assert data["content_type"] == "image/png"
    assert data["size"] == len(body)
    saved_path = Path(tmp_path) / data["path"].removeprefix("/uploads/")
    assert saved_path.read_bytes() == body


def test_upload_image_rejects_unsupported_type(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))

    resp = client.post(
        UPLOAD_IMAGES, content=b"<svg />", headers={"content-type": "image/svg+xml"}
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == 40003


def test_upload_image_rejects_empty_body(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))

    resp = client.post(
        UPLOAD_IMAGES, content=b"", headers={"content-type": "image/png"}
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == 40003


def test_upload_image_rejects_size_limit(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "image_upload_max_bytes", 4)

    resp = client.post(
        UPLOAD_IMAGES, content=b"12345", headers={"content-type": "image/png"}
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == 40003
