/**
 * 桌面 intent 分享目标与 share URL 拼装（share-poster，PRD §4.5/§4.6、design D5）。
 *
 * 各平台 share URL 携带随当前语言的文案与链接，市场内容作为不翻译变量注入。
 * 文案与链接在调用点用 i18n 插值后传入，本模块只负责 URL 构造与 label key 映射。
 */

/** 桌面 intent 分享平台。 */
export type ShareIntentTarget = 'x' | 'telegram' | 'facebook' | 'reddit';

export const SHARE_INTENT_TARGETS = [
  'x',
  'telegram',
  'facebook',
  'reddit',
] as const satisfies readonly ShareIntentTarget[];

/** 平台 → i18n label key（en/zh 文案见 shared/i18n/resources 的 `share.intent.*`）。 */
export const SHARE_INTENT_LABEL_KEY = {
  x: 'share.intent.x',
  telegram: 'share.intent.telegram',
  facebook: 'share.intent.facebook',
  reddit: 'share.intent.reddit',
} as const satisfies Record<ShareIntentTarget, string>;

/** 按平台构造 intent 分享 URL；`url`/`text` 均经 `encodeURIComponent`。 */
export function buildShareIntentUrl(
  target: ShareIntentTarget,
  url: string,
  text: string,
): string {
  const encodedUrl = encodeURIComponent(url);
  const encodedText = encodeURIComponent(text);

  switch (target) {
    case 'x':
      return `https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`;
    case 'telegram':
      return `https://t.me/share/url?url=${encodedUrl}&text=${encodedText}`;
    case 'facebook':
      return `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}&quote=${encodedText}`;
    case 'reddit':
      return `https://www.reddit.com/submit?url=${encodedUrl}&title=${encodedText}`;
  }
}
