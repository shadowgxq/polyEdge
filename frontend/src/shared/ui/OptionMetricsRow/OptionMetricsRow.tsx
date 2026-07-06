import clsx from 'clsx';
import { useTranslation } from 'react-i18next';

import { BiasLabel, type BiasCategory } from '../BiasLabel';
import styles from './OptionMetricsRow.module.css';

export type OptionMetricsRowProps = {
  /** 选项名（市场内容，英文源文本原样展示，不翻译）。 */
  optionName: string;
  /** 隐含概率，0..1 区间的比例值，由上游算好后注入。 */
  impliedProbability: number;
  /** 热度指标，数值口径由上游决定。 */
  heat: number;
  /** 偏差评分，数值口径不变，仅本地化格式呈现。 */
  biasScore: number;
  category: BiasCategory;
  className?: string;
};

/**
 * 选项指标行（PRD §4.3 / §5.4）。
 * 呈现赔率（隐含概率）/ 热度 / 偏差评分 / 偏差标签；数值口径外部注入，
 * 基元只按当前语言本地化格式呈现（评分数值口径不变）。
 */
export function OptionMetricsRow({
  optionName,
  impliedProbability,
  heat,
  biasScore,
  category,
  className,
}: OptionMetricsRowProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;

  const probabilityText = new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(impliedProbability);
  const heatText = new Intl.NumberFormat(locale).format(heat);
  const biasScoreText = new Intl.NumberFormat(locale, {
    signDisplay: 'exceptZero',
    maximumFractionDigits: 2,
  }).format(biasScore);

  return (
    <div className={clsx(styles.row, className)}>
      <span className={styles.optionName}>{optionName}</span>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.impliedProbability')}</dt>
          <dd className={styles.metricValue}>{probabilityText}</dd>
        </div>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.heat')}</dt>
          <dd className={styles.metricValue}>{heatText}</dd>
        </div>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.biasScore')}</dt>
          <dd className={styles.metricValue}>{biasScoreText}</dd>
        </div>
      </dl>
      <BiasLabel category={category} className={styles.label} />
    </div>
  );
}
