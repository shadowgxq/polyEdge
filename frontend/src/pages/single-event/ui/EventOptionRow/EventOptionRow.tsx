import clsx from 'clsx';
import { useTranslation } from 'react-i18next';

import type { OptionAnalysis } from '../../single-event.types';
import styles from './EventOptionRow.module.css';

export type EventOptionRowProps = {
  option: OptionAnalysis;
  /** 事件是否适用偏差分析；false 时只展示原始选项数据。 */
  applicable: boolean;
};

/**
 * 单事件选项行（single-event-detail，PRD §4.3、bias-algorithm §4/§6）。
 *
 * 展示选项名 + 赔率（隐含概率）/ 热度，可分析时追加后端算好的偏差评分与三分类文案；
 * `applicable=false` 仅展示原始数据，不呈现偏差评分/标签。`excluded=true` 的选项由上层过滤，
 * 不进入该组件。
 *
 * 兜底说明：analysis-api 冻结契约的 `label` 为已本地化文案（`{zh,en}`），不含 `BiasLabel`
 * 所需的 `category` 枚举；沿用 event-list-and-input 口径，直接渲染该文案 + 中性 token 样式，
 * 前端不重算偏差分类、不臆造 category 映射（详见交付风险说明）。
 */
export function EventOptionRow({ option, applicable }: EventOptionRowProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;

  const showBias = applicable;
  const labelText = option.label ? (locale.startsWith('zh') ? option.label.zh : option.label.en) : null;

  const probabilityText = new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(option.impliedProbability);
  const heatText = new Intl.NumberFormat(locale).format(option.heat);
  const biasScoreText = new Intl.NumberFormat(locale, {
    signDisplay: 'exceptZero',
    maximumFractionDigits: 2,
  }).format(option.biasScore);

  return (
    <li className={clsx(styles.row, showBias ? styles.withBias : styles.rawOnly)}>
      <span className={styles.optionName}>
        <span className={styles.optionHeader}>
          {option.iconUrl ? (
            <img className={styles.optionIcon} src={option.iconUrl} alt="" loading="lazy" />
          ) : null}
          <span className={styles.optionText}>{option.name}</span>
        </span>
        <span className={styles.probabilityTrack} aria-hidden="true">
          <span
            className={styles.probabilityFill}
            style={{ width: `${Math.max(0, Math.min(1, option.impliedProbability)) * 100}%` }}
          />
        </span>
      </span>

      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.impliedProbability')}</dt>
          <dd className={styles.metricValue}>{probabilityText}</dd>
        </div>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.heat')}</dt>
          <dd className={styles.metricValue}>{heatText}</dd>
        </div>
        {showBias ? (
          <div className={styles.metric}>
            <dt className={styles.metricLabel}>{t('metrics.biasScore')}</dt>
            <dd className={styles.metricValue}>{biasScoreText}</dd>
          </div>
        ) : null}
      </dl>

      {showBias && labelText ? <span className={styles.biasLabel}>{labelText}</span> : null}
    </li>
  );
}
