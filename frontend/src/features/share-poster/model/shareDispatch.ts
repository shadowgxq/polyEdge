/**
 * 分发动作（share-poster，PRD §4.5、design D5）。
 *
 * 纯命令式 helper：Web Share 分享图片文件、下载图片、复制图片、复制链接、intent 分享。
 * 能力探测在 `shareCapabilities` 完成；本模块只在动作边界再做一次文件级确认与错误归类，
 * 编排（loading / feedback / guard）由 `useSharePoster` 承载。
 */

import { buildShareIntentUrl, type ShareIntentTarget } from './shareIntents.constants';
import type { PosterImage } from './sharePoster.types';

/** Web Share 结果：分享成功 / 用户取消 / 环境不支持文件分享。 */
export type WebShareOutcome = 'shared' | 'cancelled' | 'unsupported';

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function toPosterFile(image: PosterImage): File {
  return new File([image.blob], image.fileName, { type: image.blob.type || 'image/png' });
}

/**
 * 经 Web Share API 分享海报图片文件。
 * @throws 非用户取消的分享失败时抛错，供上层呈现可重试错误态。
 */
export async function shareImageFile(image: PosterImage, text: string): Promise<WebShareOutcome> {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return 'unsupported';
  }

  const file = toPosterFile(image);
  if (typeof navigator.canShare === 'function' && !navigator.canShare({ files: [file] })) {
    return 'unsupported';
  }

  try {
    await navigator.share({ files: [file], text });
    return 'shared';
  } catch (error) {
    if (isAbortError(error)) {
      return 'cancelled';
    }
    throw error;
  }
}

/** 触发海报图片下载。 */
export function downloadPosterImage(image: PosterImage): void {
  const objectUrl = URL.createObjectURL(image.blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = image.fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

/**
 * 复制海报图片到剪贴板（条件能力）。
 * @throws 写入失败时抛错，供上层回退下载。
 */
export async function copyPosterImage(image: PosterImage): Promise<void> {
  const clipboardItem = new ClipboardItem({ [image.blob.type || 'image/png']: image.blob });
  await navigator.clipboard.write([clipboardItem]);
}

/**
 * 复制分享链接文本。
 * @throws 写入失败时抛错，供上层呈现失败反馈。
 */
export async function copyShareLink(url: string): Promise<void> {
  await navigator.clipboard.writeText(url);
}

/** 打开对应平台的 intent 分享窗口。 */
export function openShareIntent(target: ShareIntentTarget, url: string, text: string): void {
  const intentUrl = buildShareIntentUrl(target, url, text);
  window.open(intentUrl, '_blank', 'noopener,noreferrer');
}
