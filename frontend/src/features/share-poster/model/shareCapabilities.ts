/**
 * 分发能力探测（share-poster，design D5）。
 *
 * 运行时探测浏览器分发能力，用于决定入口可见性与回退：
 *   - Web Share 分享图片文件（移动端优先）
 *   - 复制图片到剪贴板（条件能力，需安全上下文 + `ClipboardItem`）
 *   - 复制链接文本
 * 不可用能力对应入口隐藏并保留可用回退（下载 / 复制链接）。
 */

import type { ShareCapabilities } from './sharePoster.types';

const UNSUPPORTED: ShareCapabilities = {
  canWebShareFiles: false,
  canCopyImage: false,
  canCopyLink: false,
};

export function detectShareCapabilities(): ShareCapabilities {
  if (typeof navigator === 'undefined') {
    return UNSUPPORTED;
  }

  const canWebShareFiles =
    typeof navigator.share === 'function' && typeof navigator.canShare === 'function';

  const isSecureContext = typeof window !== 'undefined' ? window.isSecureContext : false;
  const canCopyImage =
    isSecureContext &&
    typeof navigator.clipboard?.write === 'function' &&
    typeof window !== 'undefined' &&
    typeof window.ClipboardItem !== 'undefined';

  const canCopyLink = typeof navigator.clipboard?.writeText === 'function';

  return { canWebShareFiles, canCopyImage, canCopyLink };
}
