/**
 * 分享出图 / 分发编排 hook（share-poster，design D7）。
 *
 * 出图与分发是一次性命令式动作（非服务端态），用本地组件态承载 loading / error，不引入 Query。
 * 负责：受控离屏节点出图（`document.fonts.ready` + 图片 decode 后触发）、能力探测、
 * 各分发动作的 pending 防重与结果反馈、出图失败可重试。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { capturePoster } from './posterCapture';
import { detectShareCapabilities } from './shareCapabilities';
import {
  copyPosterImage,
  copyShareLink,
  downloadPosterImage,
  openShareIntent,
  shareImageFile,
} from './shareDispatch';
import type { ShareIntentTarget } from './shareIntents.constants';
import type { PosterImage, ShareCapabilities } from './sharePoster.types';

export type PosterCaptureState = 'idle' | 'capturing' | 'ready' | 'error';

export type ShareActionKey = 'webShare' | 'download' | 'copyImage' | 'copyLink';

export type ShareFeedback = {
  tone: 'success' | 'error';
  messageKey: string;
};

export type UseSharePosterParams = {
  /** 分享链接；缺省用当前页 URL。 */
  shareUrl?: string;
  /** 已本地化的分享文案（市场内容作变量注入），用于 Web Share 与 intent 分享。 */
  shareText: string;
};

export type UseSharePosterResult = {
  posterRef: React.RefObject<HTMLDivElement>;
  captureState: PosterCaptureState;
  previewUrl: string | null;
  capabilities: ShareCapabilities;
  feedback: ShareFeedback | null;
  pendingAction: ShareActionKey | null;
  isReady: boolean;
  retryCapture: () => void;
  shareViaWebShare: () => Promise<void>;
  downloadImage: () => void;
  copyImage: () => Promise<void>;
  copyLink: () => Promise<void>;
  shareToIntent: (target: ShareIntentTarget) => void;
};

function resolveShareUrl(shareUrl: string | undefined): string {
  if (shareUrl) {
    return shareUrl;
  }
  return typeof window !== 'undefined' ? window.location.href : '';
}

export function useSharePoster({
  shareUrl,
  shareText,
}: UseSharePosterParams): UseSharePosterResult {
  const posterRef = useRef<HTMLDivElement>(null);
  const [captureState, setCaptureState] = useState<PosterCaptureState>('idle');
  const [posterImage, setPosterImage] = useState<PosterImage | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<ShareFeedback | null>(null);
  const [pendingAction, setPendingAction] = useState<ShareActionKey | null>(null);

  const capabilities = useMemo(() => detectShareCapabilities(), []);

  // 出图：hook 随分享弹窗打开挂载（关闭即卸载），idle 时对离屏节点触发一次受控出图。
  useEffect(() => {
    if (captureState !== 'idle') {
      return;
    }
    const node = posterRef.current;
    if (!node) {
      return;
    }

    let isCancelled = false;
    setCaptureState('capturing');

    capturePoster(node)
      .then((image) => {
        if (isCancelled) {
          return;
        }
        setPosterImage(image);
        setPreviewUrl(URL.createObjectURL(image.blob));
        setCaptureState('ready');
      })
      .catch(() => {
        if (!isCancelled) {
          setCaptureState('error');
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [captureState]);

  // previewUrl 变化或卸载时释放上一份 object URL。
  useEffect(() => {
    if (!previewUrl) {
      return;
    }
    return () => {
      URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const retryCapture = useCallback(() => {
    setPosterImage(null);
    setPreviewUrl(null);
    setFeedback(null);
    setCaptureState('idle');
  }, []);

  const runImageAction = useCallback(
    async (
      key: ShareActionKey,
      action: (image: PosterImage) => Promise<void> | void,
      result: { successKey?: string; errorKey: string },
    ) => {
      if (pendingAction || !posterImage) {
        return;
      }
      setPendingAction(key);
      setFeedback(null);
      try {
        await action(posterImage);
        if (result.successKey) {
          setFeedback({ tone: 'success', messageKey: result.successKey });
        }
      } catch {
        setFeedback({ tone: 'error', messageKey: result.errorKey });
      } finally {
        setPendingAction(null);
      }
    },
    [pendingAction, posterImage],
  );

  const shareViaWebShare = useCallback(async () => {
    if (pendingAction || !posterImage) {
      return;
    }
    setPendingAction('webShare');
    setFeedback(null);
    try {
      const outcome = await shareImageFile(posterImage, shareText);
      if (outcome === 'unsupported') {
        setFeedback({ tone: 'error', messageKey: 'share.feedback.webShareError' });
      }
    } catch {
      setFeedback({ tone: 'error', messageKey: 'share.feedback.webShareError' });
    } finally {
      setPendingAction(null);
    }
  }, [pendingAction, posterImage, shareText]);

  const downloadImage = useCallback(() => {
    if (!posterImage) {
      return;
    }
    downloadPosterImage(posterImage);
    setFeedback({ tone: 'success', messageKey: 'share.feedback.downloadSuccess' });
  }, [posterImage]);

  const copyImage = useCallback(
    () =>
      runImageAction('copyImage', (image) => copyPosterImage(image), {
        successKey: 'share.feedback.copyImageSuccess',
        errorKey: 'share.feedback.copyImageError',
      }),
    [runImageAction],
  );

  const copyLink = useCallback(async () => {
    if (pendingAction) {
      return;
    }
    setPendingAction('copyLink');
    setFeedback(null);
    try {
      await copyShareLink(resolveShareUrl(shareUrl));
      setFeedback({ tone: 'success', messageKey: 'share.feedback.copyLinkSuccess' });
    } catch {
      setFeedback({ tone: 'error', messageKey: 'share.feedback.copyLinkError' });
    } finally {
      setPendingAction(null);
    }
  }, [pendingAction, shareUrl]);

  const shareToIntent = useCallback(
    (target: ShareIntentTarget) => {
      openShareIntent(target, resolveShareUrl(shareUrl), shareText);
    },
    [shareUrl, shareText],
  );

  return {
    posterRef,
    captureState,
    previewUrl,
    capabilities,
    feedback,
    pendingAction,
    isReady: captureState === 'ready' && posterImage !== null,
    retryCapture,
    shareViaWebShare,
    downloadImage,
    copyImage,
    copyLink,
    shareToIntent,
  };
}
