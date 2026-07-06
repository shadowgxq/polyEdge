import clsx from 'clsx';
import { useTranslation } from 'react-i18next';

import type { IsoDateTimeString } from '../../../services/types';
import styles from './SnapshotTime.module.css';

export type SnapshotTimeProps = {
  /** 数据快照时间（Polymarket 数据获取时间），ISO 8601 字符串。 */
  snapshotAt: IsoDateTimeString;
  className?: string;
};

/**
 * 数据快照时间标注（PRD §5.3 / §4.5）。
 * 语义固定为「数据快照时间」，与「海报生成时间」区分展示
 * （海报生成时间由 share change 提供）。时间格式随语言本地化。
 */
export function SnapshotTime({ snapshotAt, className }: SnapshotTimeProps) {
  const { t, i18n } = useTranslation();
  const snapshotDate = new Date(snapshotAt);

  if (Number.isNaN(snapshotDate.getTime())) {
    return null;
  }

  const formattedTime = new Intl.DateTimeFormat(i18n.language, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(snapshotDate);

  return (
    <time className={clsx(styles.snapshot, className)} dateTime={snapshotAt}>
      {t('snapshot.dataTime', { time: formattedTime })}
    </time>
  );
}
