import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { Copy, Download, ExternalLink, Link2, Share2, X } from '../../../../shared/icons';
import { ErrorState } from '../../../../shared/ui/ErrorState';
import type { SharePosterContent } from '../../model/sharePoster.types';
import {
  SHARE_INTENT_LABEL_KEY,
  SHARE_INTENT_TARGETS,
} from '../../model/shareIntents.constants';
import { useSharePoster } from '../../model/useSharePoster';
import { SharePosterCard } from '../SharePosterCard';
import styles from './SharePosterDialog.module.css';

export type SharePosterDialogProps = {
  content: SharePosterContent;
};

/**
 * 分享弹窗内容（share-poster，design D7、PRD §4.5、§5.2）。
 *
 * 随 `Dialog.Root` 开合挂载 / 卸载（关闭即卸载复位一次性态）。承载出图预览、分发动作
 * 与降级 / 失败态：出图中占位、出图失败 `ErrorState` + 重试，就绪后按能力探测暴露
 * Web Share / 下载 / 复制图片 / 复制链接 / intent 分享入口，缺失能力对应入口隐藏并保留
 * 可用回退。离屏海报节点为出图源，随弹窗打开挂载。
 */
export function SharePosterDialog({ content }: SharePosterDialogProps) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className={styles.overlay} />
      <Dialog.Content className={styles.content}>
        <SharePosterDialogBody content={content} />
      </Dialog.Content>
    </Dialog.Portal>
  );
}

function SharePosterDialogBody({ content }: SharePosterDialogProps) {
  const { t } = useTranslation();

  const shareText = t('share.intent.text', { title: content.headline });
  // 挂载即出图触发时刻 → 海报生成时间（与数据快照时间独立，design D4）。
  const generatedAt = useMemo(() => new Date(), []);

  const {
    posterRef,
    captureState,
    previewUrl,
    capabilities,
    feedback,
    pendingAction,
    isReady,
    isShareLinkReady,
    retryCapture,
    shareViaWebShare,
    downloadImage,
    copyImage,
    copyLink,
    shareToIntent,
  } = useSharePoster({ shareText });

  const areActionsDisabled = !isReady || pendingAction !== null;

  return (
    <>
      <div className={styles.head}>
        <Dialog.Title className={styles.title}>{t('share.dialog.title')}</Dialog.Title>
        <Dialog.Close asChild>
          <button type="button" className={styles.close} aria-label={t('share.dialog.close')}>
            <X className={styles.icon} aria-hidden="true" />
          </button>
        </Dialog.Close>
      </div>

      <Dialog.Description className={styles.description}>
        {t('share.dialog.description')}
      </Dialog.Description>

      <div className={styles.layout}>
        <div className={styles.preview}>
          {captureState === 'error' ? (
            <ErrorState
              title={t('share.dialog.captureErrorTitle')}
              description={t('share.dialog.captureErrorHint')}
              retryLabel={t('share.dialog.retry')}
              onRetry={retryCapture}
            />
          ) : isReady && previewUrl ? (
            <img className={styles.previewImage} src={previewUrl} alt={t('share.dialog.previewAlt')} />
          ) : (
            <p className={styles.generating} role="status" aria-busy="true">
              {t('share.dialog.generating')}
            </p>
          )}
        </div>

        {captureState !== 'error' ? (
          <div className={styles.controls}>
            <div className={styles.actions}>
              {capabilities.canWebShareFiles ? (
                <button
                  type="button"
                  className={clsx(styles.action, styles.primary)}
                  onClick={() => void shareViaWebShare()}
                  disabled={areActionsDisabled}
                >
                  <Share2 className={styles.icon} aria-hidden="true" />
                  {t('share.action.webShare')}
                </button>
              ) : null}

              <button
                type="button"
                className={styles.action}
                onClick={downloadImage}
                disabled={areActionsDisabled}
              >
                <Download className={styles.icon} aria-hidden="true" />
                {t('share.action.download')}
              </button>

              {capabilities.canCopyImage ? (
                <button
                  type="button"
                  className={styles.action}
                  onClick={() => void copyImage()}
                  disabled={areActionsDisabled}
                >
                  <Copy className={styles.icon} aria-hidden="true" />
                  {t('share.action.copyImage')}
                </button>
              ) : null}

              {capabilities.canCopyLink ? (
                <button
                  type="button"
                  className={styles.action}
                  onClick={() => void copyLink()}
                  disabled={pendingAction !== null || !isShareLinkReady}
                >
                  <Link2 className={styles.icon} aria-hidden="true" />
                  {t('share.action.copyLink')}
                </button>
              ) : null}
            </div>

            <div className={styles.intents}>
              <span className={styles.intentsLabel}>{t('share.intent.label')}</span>
              <div className={styles.intentsRow}>
                {SHARE_INTENT_TARGETS.map((target) => {
                  const platform = t(SHARE_INTENT_LABEL_KEY[target]);
                  return (
                    <button
                      key={target}
                      type="button"
                      className={styles.action}
                      onClick={() => shareToIntent(target)}
                      disabled={!isShareLinkReady}
                      aria-label={t('share.intent.aria', { platform })}
                    >
                      <ExternalLink className={styles.icon} aria-hidden="true" />
                      {platform}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <p
        className={clsx(
          styles.feedback,
          feedback?.tone === 'success' && styles.feedbackSuccess,
          feedback?.tone === 'error' && styles.feedbackError,
        )}
        role="status"
        aria-live="polite"
      >
        {feedback ? t(feedback.messageKey) : ''}
      </p>

      <div className={styles.offscreen} aria-hidden="true">
        <SharePosterCard ref={posterRef} content={content} generatedAt={generatedAt} />
      </div>
    </>
  );
}
