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
import type { PosterImage, ShareCapabilities, UploadedPosterImage } from './sharePoster.types';
import { uploadPosterImage } from './uploadPosterImage';

export type PosterCaptureState = 'idle' | 'capturing' | 'ready' | 'error';

export type ShareActionKey = 'webShare' | 'download' | 'copyImage' | 'copyLink';

export type ShareFeedback = {
  tone: 'success' | 'error';
  messageKey: string;
};

const CAPTURE_WATCHDOG_MS = 12000;

export type UseSharePosterParams = {
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
  isShareLinkReady: boolean;
  retryCapture: () => void;
  shareViaWebShare: () => Promise<void>;
  downloadImage: () => void;
  copyImage: () => Promise<void>;
  copyLink: () => Promise<void>;
  shareToIntent: (target: ShareIntentTarget) => void;
};

function logCaptureProgress(message: string, detail?: Record<string, unknown>): void {
  if (import.meta.env.DEV) {
    console.info(`[share-poster] ${message}`, detail ?? '');
  }
}

export function useSharePoster({
  shareText,
}: UseSharePosterParams): UseSharePosterResult {
  const posterRef = useRef<HTMLDivElement>(null);
  const [captureState, setCaptureState] = useState<PosterCaptureState>('idle');
  const [captureAttempt, setCaptureAttempt] = useState(0);
  const [posterImage, setPosterImage] = useState<PosterImage | null>(null);
  const [uploadedImage, setUploadedImage] = useState<UploadedPosterImage | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<ShareFeedback | null>(null);
  const [pendingAction, setPendingAction] = useState<ShareActionKey | null>(null);

  const capabilities = useMemo(() => detectShareCapabilities(), []);
  const captureRequestIdRef = useRef(0);
  const uploadRequestIdRef = useRef(0);

  // 出图：hook 随分享弹窗打开挂载触发一次；重试只递增 attempt，不依赖 captureState 避免清理竞态。
  useEffect(() => {
    const requestId = captureRequestIdRef.current + 1;
    captureRequestIdRef.current = requestId;
    logCaptureProgress('state:capturing', { requestId });

    let watchdogId: number | undefined;

    const frameId = window.requestAnimationFrame(() => {
      setCaptureState('capturing');
      watchdogId = window.setTimeout(() => {
        if (captureRequestIdRef.current !== requestId) {
          return;
        }
        logCaptureProgress('watchdog:timeout', { requestId });
        setCaptureState('error');
      }, CAPTURE_WATCHDOG_MS);

      const node = posterRef.current;
      if (!node) {
        if (watchdogId !== undefined) {
          window.clearTimeout(watchdogId);
        }
        logCaptureProgress('ref:missing', { requestId });
        setCaptureState('error');
        return;
      }

      logCaptureProgress('capture:start', { requestId });

      capturePoster(node, {
        onProgress: (phase, detail) => {
          logCaptureProgress(`capture:${phase}`, { requestId, ...detail });
        },
      })
        .then((image) => {
          if (captureRequestIdRef.current !== requestId) {
            return;
          }
          if (watchdogId !== undefined) {
            window.clearTimeout(watchdogId);
          }
          logCaptureProgress('capture:ready', { requestId, size: image.blob.size });
          setPosterImage(image);
          setUploadedImage(null);
          setPreviewUrl(URL.createObjectURL(image.blob));
          setCaptureState('ready');
        })
        .catch((error: unknown) => {
          if (captureRequestIdRef.current !== requestId) {
            return;
          }
          if (watchdogId !== undefined) {
            window.clearTimeout(watchdogId);
          }
          logCaptureProgress('capture:error', {
            requestId,
            error: error instanceof Error ? error.message : String(error),
          });
          setCaptureState('error');
        });
    });

    return () => {
      captureRequestIdRef.current += 1;
      window.cancelAnimationFrame(frameId);
      if (watchdogId !== undefined) {
        window.clearTimeout(watchdogId);
      }
    };
  }, [captureAttempt]);

  useEffect(() => {
    if (!posterImage) {
      return;
    }

    const requestId = uploadRequestIdRef.current + 1;
    uploadRequestIdRef.current = requestId;

    uploadPosterImage(posterImage)
      .then((image) => {
        if (uploadRequestIdRef.current !== requestId) {
          return;
        }
        setUploadedImage(image);
      })
      .catch((error: unknown) => {
        if (uploadRequestIdRef.current !== requestId) {
          return;
        }
        logCaptureProgress('upload:error', {
          requestId,
          error: error instanceof Error ? error.message : String(error),
        });
        setUploadedImage(null);
        setFeedback((current) =>
          current ? current : { tone: 'error', messageKey: 'share.feedback.uploadError' },
        );
      });

    return () => {
      uploadRequestIdRef.current += 1;
    };
  }, [posterImage]);

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
    captureRequestIdRef.current += 1;
    uploadRequestIdRef.current += 1;
    setPosterImage(null);
    setUploadedImage(null);
    setPreviewUrl(null);
    setFeedback(null);
    setCaptureState('idle');
    setCaptureAttempt((attempt) => attempt + 1);
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
    if (pendingAction || !uploadedImage) {
      return;
    }
    setPendingAction('copyLink');
    setFeedback(null);
    try {
      await copyShareLink(uploadedImage.url);
      setFeedback({ tone: 'success', messageKey: 'share.feedback.copyLinkSuccess' });
    } catch {
      setFeedback({ tone: 'error', messageKey: 'share.feedback.copyLinkError' });
    } finally {
      setPendingAction(null);
    }
  }, [pendingAction, uploadedImage]);

  const shareToIntent = useCallback(
    (target: ShareIntentTarget) => {
      if (!uploadedImage) {
        return;
      }
      openShareIntent(target, uploadedImage.url, shareText);
    },
    [shareText, uploadedImage],
  );

  return {
    posterRef,
    captureState,
    previewUrl,
    capabilities,
    feedback,
    pendingAction,
    isReady: captureState === 'ready' && posterImage !== null,
    isShareLinkReady: uploadedImage !== null,
    retryCapture,
    shareViaWebShare,
    downloadImage,
    copyImage,
    copyLink,
    shareToIntent,
  };
}
