"""图片代理端点安全约束测试。

用 httpx.MockTransport 替换出站客户端，逐条覆盖 data-source §3 的 SSRF 约束：
白名单 / 仅 https / 仅 image-* / 大小上限 / 超时 / 禁跨域重定向，以及成功代理与
白名单内重定向复检放行。校验失败一律走 BusinessException + 全局 handler 统一错误响应。
"""

from collections.abc import Callable

import httpx
import pytest

from app.core.config import settings
from app.services import image_proxy_service

PROXY = "/api/v1/image-proxy"

# 白名单默认含 polymarket.com（后缀域匹配），用其子域构造合法目标。
VALID_URL = "https://images.polymarket.com/market.png"


def _patch_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    """把出站客户端换成 MockTransport，返回被实际发出的请求列表（供断言）。"""
    seen: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def build_mock_client() -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(recording_handler),
            follow_redirects=False,
        )

    monkeypatch.setattr(image_proxy_service, "_build_client", build_mock_client)
    return seen


def _image_handler(
    content: bytes = b"\x89PNG\r\n\x1a\n-fake",
    content_type: str = "image/png",
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": content_type}, content=content
        )

    return handler


def test_valid_image_proxied(client, monkeypatch):
    body = b"\x89PNG\r\n\x1a\n-image-bytes"
    _patch_transport(monkeypatch, _image_handler(content=body))

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content == body


def test_missing_url_rejected(client, monkeypatch):
    seen = _patch_transport(monkeypatch, _image_handler())

    resp = client.get(PROXY)

    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    assert seen == []  # 未发起任何出站请求


def test_empty_url_rejected(client, monkeypatch):
    seen = _patch_transport(monkeypatch, _image_handler())

    resp = client.get(PROXY, params={"url": ""})

    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    assert seen == []


def test_non_whitelist_host_rejected(client, monkeypatch):
    seen = _patch_transport(monkeypatch, _image_handler())

    resp = client.get(PROXY, params={"url": "https://evil.com/a.png"})

    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    assert seen == []


def test_lookalike_host_rejected(client, monkeypatch):
    """evil-polymarket.com / polymarket.com.attacker.com 之类伪装域必须被拒。"""
    seen = _patch_transport(monkeypatch, _image_handler())

    resp = client.get(PROXY, params={"url": "https://evil-polymarket.com/a.png"})

    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    assert seen == []


def test_non_https_rejected(client, monkeypatch):
    seen = _patch_transport(monkeypatch, _image_handler())

    resp = client.get(PROXY, params={"url": "http://images.polymarket.com/a.png"})

    assert resp.status_code == 400
    assert resp.json()["code"] == 40002
    assert seen == []


def test_non_image_content_type_rejected(client, monkeypatch):
    _patch_transport(
        monkeypatch, _image_handler(content=b"<html>", content_type="text/html")
    )

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 502
    assert resp.json()["code"] == 50201


def test_size_exceeded_declared_length_rejected(client, monkeypatch):
    """上游声明的 Content-Length 超上限直接拒绝。"""
    monkeypatch.setattr(settings, "image_proxy_max_bytes", 8)

    def handler(_request: httpx.Request) -> httpx.Response:
        # content 长度即 httpx 自动写入的 Content-Length，超过 8 字节。
        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=b"0123456789abcdef",
        )

    _patch_transport(monkeypatch, handler)

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 502
    assert resp.json()["code"] == 50201


def test_size_exceeded_streamed_rejected(client, monkeypatch):
    """未声明 Content-Length 但流式累计超上限也要中止。"""
    monkeypatch.setattr(settings, "image_proxy_max_bytes", 4)

    def handler(_request: httpx.Request) -> httpx.Response:
        def stream():
            yield b"12"
            yield b"34"
            yield b"56"  # 累计 6 > 4，此处应被中止

        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=stream(),
        )

    _patch_transport(monkeypatch, handler)

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 502
    assert resp.json()["code"] == 50201


def test_timeout_rejected(client, monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("upstream timed out")

    _patch_transport(monkeypatch, handler)

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 502
    assert resp.json()["code"] == 50201


def test_cross_domain_redirect_rejected(client, monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.com/a.png"})

    _patch_transport(monkeypatch, handler)

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 400
    assert resp.json()["code"] == 40002


def test_redirect_within_whitelist_allowed(client, monkeypatch):
    body = b"\x89PNG\r\n\x1a\n-redirected"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/market.png"):
            return httpx.Response(
                302,
                headers={"location": "https://images.polymarket.com/final.png"},
            )
        return httpx.Response(200, headers={"content-type": "image/png"}, content=body)

    _patch_transport(monkeypatch, handler)

    resp = client.get(PROXY, params={"url": VALID_URL})

    assert resp.status_code == 200
    assert resp.content == body
