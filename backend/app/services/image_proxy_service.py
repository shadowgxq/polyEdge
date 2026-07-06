"""图片代理业务逻辑层。

为海报出图提供同源安全图片代理：对目标 URL 施加防 SSRF / 开放代理约束
（白名单 / 仅 https / 仅 image-* / 大小上限 / 超时 / 禁跨域重定向，data-source §3），
校验通过后拉取上游图片并以二进制返回，供路由层包成同源二进制流。
"""

import logging
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings
from app.core.exceptions import (
    ImageProxyInvalidTargetException,
    ImageProxyUpstreamException,
)

logger = logging.getLogger(__name__)


@dataclass
class ProxiedImage:
    """代理拉取到的图片：校验通过的内容类型与二进制内容。"""

    media_type: str
    content: bytes


def _build_client() -> httpx.Client:
    """构造出站 HTTP 客户端；关闭自动重定向以便逐跳复检白名单。

    抽成模块函数便于测试注入 MockTransport。
    """
    timeout = httpx.Timeout(settings.image_proxy_timeout_seconds)
    return httpx.Client(timeout=timeout, follow_redirects=False)


def _host_in_whitelist(host: str) -> bool:
    """精确域名或后缀域匹配，拒绝 evil-polymarket.com 之类伪装域。"""
    host = host.lower()
    for allowed in settings.image_proxy_allowed_hosts:
        allowed = allowed.lower().strip()
        if not allowed:
            continue
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def _validate_target(target_url: str | None) -> str:
    """发起出站请求前的前置校验：非空、仅 https、host 命中白名单。

    任一不满足抛 ImageProxyInvalidTargetException，且不发起任何出站请求。
    """
    if not target_url or not target_url.strip():
        raise ImageProxyInvalidTargetException("Missing image target url")

    parsed = urlparse(target_url.strip())
    if parsed.scheme != "https":
        raise ImageProxyInvalidTargetException("Only https target is allowed")

    host = parsed.hostname
    if not host or not _host_in_whitelist(host):
        raise ImageProxyInvalidTargetException("Target host is not allowed")

    return target_url.strip()


def _validate_content_type(response: httpx.Response) -> str:
    """仅允许 image/* 内容类型，否则中止并抛上游异常，不回传响应体。"""
    content_type = response.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    if not media_type.startswith("image/"):
        raise ImageProxyUpstreamException("Upstream content type is not an image")
    return media_type


def _fetch(client: httpx.Client, url: str, redirects_left: int) -> httpx.Response:
    """发起一次出站请求；遇 3xx 逐跳复检「仅 https + 白名单」后受控再拉取。

    返回一个仍处于流式打开状态的响应（调用方负责读取并关闭）。
    """
    request = client.build_request("GET", url)
    response = client.send(request, stream=True)

    if response.is_redirect:
        location = response.headers.get("location")
        response.close()
        if redirects_left <= 0:
            raise ImageProxyUpstreamException("Too many redirects")
        if not location:
            raise ImageProxyUpstreamException("Redirect without location")
        # 相对跳转按当前 URL 解析为绝对地址，再复用同一套目标校验。
        next_url = urljoin(url, location)
        _validate_target(next_url)
        return _fetch(client, next_url, redirects_left - 1)

    if response.status_code >= 400:
        response.close()
        raise ImageProxyUpstreamException(
            f"Upstream responded with status {response.status_code}"
        )

    return response


def _read_limited(response: httpx.Response, max_bytes: int) -> bytes:
    """大小上限双重保护：先看声明的 Content-Length，再流式累加实际字节。

    任一超限即中止拉取并抛上游异常，不回传超限内容。
    """
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > max_bytes:
                raise ImageProxyUpstreamException("Upstream image exceeds size limit")
        except ValueError:
            # Content-Length 非法则忽略声明，交由下方流式读取兜底。
            pass

    buffer = bytearray()
    for chunk in response.iter_bytes():
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise ImageProxyUpstreamException("Upstream image exceeds size limit")
    return bytes(buffer)


def fetch_image(target_url: str | None) -> ProxiedImage:
    """代理拉取一张 Polymarket 图片，返回校验通过的内容类型与二进制内容。

    校验顺序：目标 URL（https + 白名单）→ 出站拉取（禁自动重定向 + 超时）
    → 内容类型（image/*）→ 大小上限。任一失败抛 BusinessException 子类。
    """
    validated_url = _validate_target(target_url)

    client = _build_client()
    try:
        response = _fetch(client, validated_url, settings.image_proxy_max_redirects)
        try:
            media_type = _validate_content_type(response)
            content = _read_limited(response, settings.image_proxy_max_bytes)
        finally:
            response.close()
    except httpx.TimeoutException as exc:
        raise ImageProxyUpstreamException("Upstream request timed out") from exc
    except httpx.HTTPError as exc:
        logger.warning("image_proxy upstream error: %s", exc)
        raise ImageProxyUpstreamException("Failed to fetch upstream image") from exc
    finally:
        client.close()

    return ProxiedImage(media_type=media_type, content=content)
