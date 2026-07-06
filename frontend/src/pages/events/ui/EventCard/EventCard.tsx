import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { SnapshotTime } from '../../../../shared/ui/SnapshotTime';
import type { EventCard as EventCardModel } from '../../events.types';
import styles from './EventCard.module.css';

export type EventCardProps = {
  event: EventCardModel;
};

/**
 * 单事件卡片（PRD §4.1、AC-1、design D5）。
 *
 * 展示事件名 + 各选项赔率（隐含概率）概览 + 数据快照时间。
 * `applicable=true` 时展示后端返回的概览偏差标签本地化文案并标注最大偏差选项名；
 * `applicable=false` 时标注「不适用偏差分析」，不渲染偏差标签。整卡为进入明细的链接。
 *
 * 说明：analysis-api 冻结契约的 `overview_label` 为已本地化文案（`{zh,en}`），
 * 不含 `BiasLabel` 所需的 `category` 枚举，故此处直接渲染该文案（前端不自算偏差分类）。
 */
export function EventCard({ event }: EventCardProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const overviewLabelText =
    event.overviewLabel && (locale.startsWith('zh') ? event.overviewLabel.zh : event.overviewLabel.en);

  const probabilityFormatter = new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  });

  return (
    <Link to={`/events/${event.slug}`} className={styles.card}>
      <span className={styles.title}>{event.title}</span>

      {event.applicable && overviewLabelText ? (
        <span className={styles.overview}>
          <span className={styles.overviewLabel}>{overviewLabelText}</span>
          {event.overviewOptionName ? (
            <span className={styles.topOption}>
              {t('events.card.topBiasOption', { optionName: event.overviewOptionName })}
            </span>
          ) : null}
        </span>
      ) : (
        <span className={styles.notApplicable}>{t('events.card.notApplicable')}</span>
      )}

      <ul className={styles.options}>
        {event.options.map((option) => (
          <li key={option.name} className={styles.option}>
            <span className={styles.optionName}>{option.name}</span>
            <span className={styles.optionValue}>
              {probabilityFormatter.format(option.impliedProbability)}
            </span>
          </li>
        ))}
      </ul>

      <SnapshotTime snapshotAt={event.dataSnapshotAt} className={styles.snapshot} />
    </Link>
  );
}
