/**
 * 图片代理 URL 拼装工具（share-poster，PRD §1.4、design D3）。
 *
 * 把 Polymarket 图片原始 URL 改写为同源 `GET /api/v1/image-proxy?url=<原图URL>`，
 * 走 `shared/api` 统一基址（`requestClient.defaults.baseURL`）；海报组件不直连
 * Polymarket 图片域，以规避出图时的 canvas 跨域污染。
 */

import { requestClient } from '../../../shared/api';

const IMAGE_PROXY_PATH = '/api/v1/image-proxy';

/**
 * 构造经后端图片代理的同源图片 URL。
 * 基址为空（同源部署）时返回相对路径 `/api/v1/image-proxy?url=...`。
 */
export function buildImageProxyUrl(originalUrl: string): string {
  const baseUrl = requestClient.defaults.baseURL ?? '';
  const normalizedBase = baseUrl.replace(/\/+$/, '');
  return `${normalizedBase}${IMAGE_PROXY_PATH}?url=${encodeURIComponent(originalUrl)}`;
}
