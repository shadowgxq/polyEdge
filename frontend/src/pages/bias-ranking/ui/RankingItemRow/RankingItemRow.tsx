import clsx from 'clsx';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { ChevronRight } from '../../../../shared/icons';
import type { BiasCategory } from '../../../../shared/ui/BiasLabel';
import type { RankingItem } from '../../bias-ranking.types';
import styles from './RankingItemRow.module.css';

export type RankingItemRowProps = {
  item: RankingItem;
  /** 由所属榜别注入的信号色档（过热/观察/合理 → hot/cold/fair tone）。 */
  category: BiasCategory;
};

/** 榜别信号色档 → 卡片信号色类名（左缘信号带 + 概率条着色 + 标签色）。 */
const SIGNAL_CLASS_BY_CATEGORY = {
  hot: styles.hot,
  cold: styles.cold,
  fair: styles.fair,
} as const satisfies Record<BiasCategory, string>;

/** 概率百分比转进度条宽度（钳制 0..100）。 */
function toBarWidth(impliedProbability: number): string {
  const clamped = Math.max(0, Math.min(1, impliedProbability));
  return `${(clamped * 100).toFixed(1)}%`;
}

/**
 * 单条榜单项（bias-ranking，bias-multi-signal）。
 *
 * 展示所属事件标题、选项名、赔率（隐含概率）、偏差评分（交易集中度残差）与该选项自己的
 * 八类诚实标签文案；整行为回跳 `/events/:eventId` 的只读入口，键盘可达，`aria-label`
 * 经 i18n 插值呈现事件名/选项名，不字符串拼接。无任何交易入口。
 *
 * 行信号色由 `category`（榜别 → 过热/观察/合理）注入；标签文案取自后端已本地化的
 * `item.label`（前端不重算偏差、不反推分类）。
 */
export function RankingItemRow({ item, category }: RankingItemRowProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;

  const probabilityText = new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(item.impliedProbability);
  const biasScoreText = new Intl.NumberFormat(locale, {
    signDisplay: 'exceptZero',
    maximumFractionDigits: 2,
  }).format(item.biasScore);
  const labelText = locale.startsWith('zh') ? item.label.zh : item.label.en;

  return (
    <Link
      to={`/events/${item.eventSlug}`}
      className={clsx(styles.row, SIGNAL_CLASS_BY_CATEGORY[category])}
      aria-label={t('ranking.item.aria', {
        eventTitle: item.eventTitle,
        optionName: item.optionName,
      })}
    >
      <span className={styles.eventTitle}>{item.eventTitle}</span>
      <span className={styles.optionName}>{item.optionName}</span>

      <span className={styles.bar} aria-hidden="true">
        <span className={styles.barFill} style={{ width: toBarWidth(item.impliedProbability) }} />
      </span>

      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.impliedProbability')}</dt>
          <dd className={styles.metricValue}>{probabilityText}</dd>
        </div>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.biasScore')}</dt>
          <dd className={clsx(styles.metricValue, styles.biasScore)}>{biasScoreText}</dd>
        </div>
      </dl>

      <span className={styles.label}>{labelText}</span>
      <span className={styles.cta} aria-hidden="true">
        <ChevronRight className={styles.ctaIcon} />
      </span>
    </Link>
  );
}
