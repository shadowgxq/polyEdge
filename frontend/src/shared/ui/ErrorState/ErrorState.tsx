import clsx from 'clsx';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import styles from './ErrorState.module.css';

export type ErrorStateProps = {
  /** 错误标题，缺省用 i18n `error.title`。 */
  title?: string;
  /** 错误说明，缺省用 i18n `error.description`。 */
  description?: string;
  /** 重试回调；提供时渲染重试入口。 */
  onRetry?: () => void;
  /** 重试按钮文案，缺省用 i18n `error.retry`。 */
  retryLabel?: string;
  /** 额外操作插槽（如切 Tab）。 */
  action?: ReactNode;
  className?: string;
};

/**
 * 通用错误态（PRD §5.2、AC-5）。
 * 拉取失败等场景呈现可理解反馈 + 重试入口；不静默失败、不整页报错。
 */
export function ErrorState({
  title,
  description,
  onRetry,
  retryLabel,
  action,
  className,
}: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div className={clsx(styles.root, className)} role="alert">
      <p className={styles.title}>{title ?? t('error.title')}</p>
      <p className={styles.description}>{description ?? t('error.description')}</p>
      {onRetry || action ? (
        <div className={styles.actions}>
          {onRetry ? (
            <button type="button" className={styles.retry} onClick={onRetry}>
              {retryLabel ?? t('error.retry')}
            </button>
          ) : null}
          {action}
        </div>
      ) : null}
    </div>
  );
}
