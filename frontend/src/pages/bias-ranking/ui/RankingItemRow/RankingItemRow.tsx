import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { BiasLabel, type BiasCategory } from '../../../../shared/ui/BiasLabel';
import type { RankingItem } from '../../bias-ranking.types';
import styles from './RankingItemRow.module.css';

export type RankingItemRowProps = {
  item: RankingItem;
  /** 由所属榜别注入的三分类（design D2）；驱动 `BiasLabel` 信号色与文案。 */
  category: BiasCategory;
};

/**
 * 单条榜单项（bias-ranking，design D2/D7、AC-4/AC-7）。
 *
 * 展示所属事件标题、选项名、赔率（隐含概率）、偏差评分与 `BiasLabel`；
 * 整行为回跳 `/events/:eventId`（`event_slug` 作参数）的只读入口，键盘可达，
 * `aria-label` 经 i18n 插值呈现事件名/选项名，不字符串拼接。无任何交易入口。
 *
 * 偏差分类由 `category`（榜别映射）注入，前端不重算偏差；后端 `label` 文案仅备用不渲染。
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

  return (
    <Link
      to={`/events/${item.eventSlug}`}
      className={styles.row}
      aria-label={t('ranking.item.aria', {
        eventTitle: item.eventTitle,
        optionName: item.optionName,
      })}
    >
      <span className={styles.eventTitle}>{item.eventTitle}</span>
      <span className={styles.optionName}>{item.optionName}</span>

      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.impliedProbability')}</dt>
          <dd className={styles.metricValue}>{probabilityText}</dd>
        </div>
        <div className={styles.metric}>
          <dt className={styles.metricLabel}>{t('metrics.biasScore')}</dt>
          <dd className={styles.metricValue}>{biasScoreText}</dd>
        </div>
      </dl>

      <BiasLabel category={category} className={styles.label} />
    </Link>
  );
}
