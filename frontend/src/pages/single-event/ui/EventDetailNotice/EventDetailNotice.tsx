import clsx from 'clsx';

import styles from './EventDetailNotice.module.css';

export type EventDetailNoticeProps = {
  /** 已本地化标注标题（如「纯交易热度」「不适用偏差分析」）。 */
  title: string;
  /** 可选说明文案。 */
  description?: string;
  className?: string;
};

/**
 * 事件级边界 / 降级标注条（single-event-detail，bias-algorithm §3.5/§6）。
 * 纯展示：文案由页面经 i18n 注入；语义固定为数据降级（warn），不表现为空白省略。
 */
export function EventDetailNotice({ title, description, className }: EventDetailNoticeProps) {
  return (
    <div className={clsx(styles.notice, className)} role="status">
      <span className={styles.title}>{title}</span>
      {description ? <span className={styles.description}>{description}</span> : null}
    </div>
  );
}
