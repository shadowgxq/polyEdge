import clsx from 'clsx';
import type { ReactNode } from 'react';

import styles from './EmptyState.module.css';

export type EmptyStateProps = {
  /** 空态标题，已本地化文案由调用方注入。 */
  title: string;
  /** 可选说明，引导用户下一步。 */
  description?: string;
  /** 可选操作插槽（如切回热门 Tab）。 */
  action?: ReactNode;
  className?: string;
};

/**
 * 通用空态（PRD §5.2、AC-5）。
 * 支撑各降级场景（无匹配事件 / 无入榜项等）；不呈现空白列表。
 * 文案由调用方经 i18n 注入。
 */
export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={clsx(styles.root, className)} role="status">
      <p className={styles.title}>{title}</p>
      {description ? <p className={styles.description}>{description}</p> : null}
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
