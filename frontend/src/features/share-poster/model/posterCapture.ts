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
const FALLBACK_BACKGROUND = '#ffffff';
const FONT_READY_TIMEOUT_MS = 1500;
const IMAGE_READY_TIMEOUT_MS = 4000;
const CAPTURE_TIMEOUT_MS = 8000;

export type PosterCapturePhase =
  | 'font:start'
  | 'font:ready'
  | 'images:start'
  | 'images:ready'
  | 'measure:start'
  | 'measure:ready'
  | 'toBlob:start'
  | 'toBlob:ready';

export type CapturePosterOptions = {
  onProgress?: (phase: PosterCapturePhase, detail?: Record<string, unknown>) => void;
};

function getPixelRatio(): number {
  const ratio = typeof window !== 'undefined' ? window.devicePixelRatio : MIN_PIXEL_RATIO;
  return Math.max(Number.isFinite(ratio) && ratio > 0 ? ratio : MIN_PIXEL_RATIO, MIN_PIXEL_RATIO);
}

function buildFileName(): string {
  return `polyedge-poster-${Date.now()}.png`;
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(message)), timeoutMs);
  });

  return Promise.race([promise, timeout]).finally(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  });
}

/** 等待海报内所有图片加载并 `decode` 完成（design D3）；单图失败不阻断整体出图。 */
async function waitForImages(
  node: HTMLElement,
  onProgress?: CapturePosterOptions['onProgress'],
): Promise<void> {
  const images = Array.from(node.querySelectorAll('img'));
  onProgress?.('images:start', { count: images.length });

  await Promise.all(
    images.map(async (image) => {
      try {
        if (!image.complete) {
          await withTimeout(
            new Promise<void>((resolve) => {
              image.addEventListener('load', () => resolve(), { once: true });
              image.addEventListener('error', () => resolve(), { once: true });
            }),
            IMAGE_READY_TIMEOUT_MS,
            'share-poster: image loading timed out',
          );
        }
        if (typeof image.decode === 'function') {
          await withTimeout(
            image.decode(),
            IMAGE_READY_TIMEOUT_MS,
            'share-poster: image decoding timed out',
          );
        }
      } catch {
        // 单张图片解码失败不阻断出图；海报可在缺图情况下仍输出核心信息。
      }
    }),
  );

  onProgress?.('images:ready', { count: images.length });
}

/**
 * 对受控离屏海报节点出图。
 * @throws 出图为空或渲染失败时抛错，供上层呈现可重试错误态。
 */
export async function capturePoster(
  node: HTMLElement,
  options: CapturePosterOptions = {},
): Promise<PosterImage> {
  const { onProgress } = options;

  if (typeof document !== 'undefined' && document.fonts?.ready) {
    onProgress?.('font:start');
    await withTimeout(
      document.fonts.ready,
      FONT_READY_TIMEOUT_MS,
      'share-poster: font loading timed out',
    ).catch(() => {
      // 外部字体不可用时使用系统字体继续出图，避免弹窗永久停在生成中。
    });
    onProgress?.('font:ready');
  }

  await waitForImages(node, onProgress);

  onProgress?.('measure:start');
  const rect = node.getBoundingClientRect();
  const width = Math.ceil(rect.width);
  const height = Math.ceil(rect.height);
  onProgress?.('measure:ready', { width, height });

  if (width <= 0 || height <= 0) {
    throw new Error('share-poster: capture target has no measurable size');
  }

  onProgress?.('toBlob:start', { width, height });
  const blob = await withTimeout(
    toBlob(node, {
      width,
      height,
      canvasWidth: width,
      canvasHeight: height,
      backgroundColor: FALLBACK_BACKGROUND,
      pixelRatio: getPixelRatio(),
      cacheBust: true,
      skipFonts: true,
      style: {
        margin: '0',
        transform: 'none',
      },
      type: POSTER_MIME,
    }),
    CAPTURE_TIMEOUT_MS,
    'share-poster: capture timed out',
  );
  onProgress?.('toBlob:ready');

  if (!blob) {
    throw new Error('share-poster: capture produced an empty image');
  }

  return { blob, fileName: buildFileName() };
}
