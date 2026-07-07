import clsx from 'clsx';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { ChevronRight } from '../../../../shared/icons';
import { SnapshotTime } from '../../../../shared/ui/SnapshotTime';
import type { EventCard as EventCardModel } from '../../events.types';
import styles from './EventCard.module.css';

export type EventCardProps = {
  event: EventCardModel;
};

/** 概率百分比转进度条宽度（钳制到 0..100，避免脏数据溢出轨道）。 */
function toBarWidth(impliedProbability: number): string {
  const clamped = Math.max(0, Math.min(1, impliedProbability));
  return `${(clamped * 100).toFixed(1)}%`;
}

/**
 * 单事件卡片（PRD §4.1、AC-1、design D5）。
 *
 * 展示事件名 + 各选项赔率（隐含概率）概览 + 数据快照时间。
 * `applicable=true` 时展示后端返回的概览偏差标签本地化文案并标注最大偏差选项名；
 * `applicable=false` 时标注「不适用偏差分析」，不渲染偏差标签。整卡为进入明细的链接。
 *
 * 概率以进度条可视化（首选项＝市场最看好项，做品牌强调），偏差方向不在卡片数据内，
 * 故只呈现强度层级、不臆造 hot/cold 着色。
 *
 * 说明：analysis-api 冻结契约的 `overview_label` 为已本地化文案（`{zh,en}`），
 * 不含 `BiasLabel` 所需的 `category` 枚举，故此处直接渲染该文案（前端不自算偏差分类）。
 */
export function EventCard({ event }: EventCardProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const overviewLabelText =
    event.applicable && event.overviewLabel
      ? locale.startsWith('zh')
        ? event.overviewLabel.zh
        : event.overviewLabel.en
      : null;

  const probabilityFormatter = new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  });

  const remainingOptions = event.optionsTotal - event.options.length;

  return (
    <Link to={`/events/${event.slug}`} className={styles.card}>
      <div className={styles.head}>
        <span className={styles.title}>{event.title}</span>
        {overviewLabelText ? (
          <span className={styles.insight}>
            <span className={styles.insightDot} aria-hidden="true" />
            <span className={styles.insightLabel}>{overviewLabelText}</span>
          </span>
        ) : (
          <span className={styles.notApplicable}>{t('events.card.notApplicable')}</span>
        )}
      </div>

      {overviewLabelText && event.overviewOptionName ? (
        <span className={styles.topOption}>
          {t('events.card.topBiasOption', { optionName: event.overviewOptionName })}
        </span>
      ) : null}

      <ul className={styles.options}>
        {event.options.map((option, index) => (
          <li
            key={`${event.slug}:${option.name}:${index}`}
            className={clsx(styles.option, index === 0 && styles.leadOption)}
          >
            <div className={styles.optionRow}>
              <span className={styles.optionIdentity}>
                {option.iconUrl ? (
                  <img className={styles.optionIcon} src={option.iconUrl} alt="" loading="lazy" />
                ) : null}
                <span className={styles.optionName}>{option.name}</span>
              </span>
              <span className={styles.optionValue}>
                {probabilityFormatter.format(option.impliedProbability)}
              </span>
            </div>
            <span className={styles.bar} aria-hidden="true">
              <span
                className={styles.barFill}
                style={{ width: toBarWidth(option.impliedProbability) }}
              />
            </span>
          </li>
        ))}
      </ul>

      <div className={styles.foot}>
        {remainingOptions > 0 ? (
          <span className={styles.moreOptions}>
            {t('events.card.moreOptions', { count: remainingOptions })}
          </span>
        ) : (
          <span />
        )}
        <SnapshotTime snapshotAt={event.dataSnapshotAt} className={styles.snapshot} />
        <span className={styles.cta} aria-hidden="true">
          <ChevronRight className={styles.ctaIcon} />
        </span>
      </div>
    </Link>
  );
}
