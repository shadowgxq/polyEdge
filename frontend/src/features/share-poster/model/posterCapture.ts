/**
 * 受控离屏海报出图 service（share-poster，PRD §4.5、design D1/D2/D3）。
 *
 * 封装 `html-to-image` 调用：出图前 `await document.fonts.ready` 并等待海报内图片
 * 加载 / `decode` 完成，再以 `pixelRatio = max(devicePixelRatio, 2)` 高清渲染、内联字体。
 * 组件不直接依赖库细节；出图失败抛错供上层降级（下载 / 重试），不静默失败。
 */

import { toBlob } from 'html-to-image';

import type { PosterImage } from './sharePoster.types';

const POSTER_MIME = 'image/png';
const MIN_PIXEL_RATIO = 2;

function getPixelRatio(): number {
  const ratio = typeof window !== 'undefined' ? window.devicePixelRatio : MIN_PIXEL_RATIO;
  return Math.max(Number.isFinite(ratio) && ratio > 0 ? ratio : MIN_PIXEL_RATIO, MIN_PIXEL_RATIO);
}

function buildFileName(): string {
  return `polyedge-poster-${Date.now()}.png`;
}

/** 等待海报内所有图片加载并 `decode` 完成（design D3）；单图失败不阻断整体出图。 */
async function waitForImages(node: HTMLElement): Promise<void> {
  const images = Array.from(node.querySelectorAll('img'));
  await Promise.all(
    images.map(async (image) => {
      try {
        if (!image.complete) {
          await new Promise<void>((resolve) => {
            image.addEventListener('load', () => resolve(), { once: true });
            image.addEventListener('error', () => resolve(), { once: true });
          });
        }
        if (typeof image.decode === 'function') {
          await image.decode();
        }
      } catch {
        // 单张图片解码失败不阻断出图；海报可在缺图情况下仍输出核心信息。
      }
    }),
  );
}

/**
 * 对受控离屏海报节点出图。
 * @throws 出图为空或渲染失败时抛错，供上层呈现可重试错误态。
 */
export async function capturePoster(node: HTMLElement): Promise<PosterImage> {
  if (typeof document !== 'undefined' && document.fonts?.ready) {
    await document.fonts.ready;
  }
  await waitForImages(node);

  const blob = await toBlob(node, {
    pixelRatio: getPixelRatio(),
    cacheBust: true,
    type: POSTER_MIME,
  });

  if (!blob) {
    throw new Error('share-poster: capture produced an empty image');
  }

  return { blob, fileName: buildFileName() };
}
