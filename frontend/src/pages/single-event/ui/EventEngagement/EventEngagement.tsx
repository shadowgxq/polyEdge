import { useTranslation } from 'react-i18next';

import type { IsoDateTimeString } from '../../../../services/types';
import { SnapshotTime } from '../../../../shared/ui/SnapshotTime';
import styles from './EventEngagement.module.css';

export type EventEngagementProps = {
  /** 事件级关注度（评论数），不参与单选项偏差。 */
  commentCount: number;
  /** 数据快照时间（ISO 8601）。 */
  snapshotAt: IsoDateTimeString;
};

/**
 * 事件级关注度与数据快照时间区块（single-event-detail，PRD §4.3/§5.3）。
 * 展示 `comment_count` 关注度标签，并经 `SnapshotTime` 基元本地化标注快照时间。
 */
export function EventEngagement({ commentCount, snapshotAt }: EventEngagementProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.engagement}>
      <span className={styles.comments}>{t('detail.commentCount', { count: commentCount })}</span>
      <SnapshotTime snapshotAt={snapshotAt} />
    </div>
  );
}
