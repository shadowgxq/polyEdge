import { useTranslation } from 'react-i18next';

import { SharePosterTrigger, type SharePosterContent } from '../../../../features/share-poster';
import type { BiasCategory } from '../../../../shared/ui/BiasLabel';
import { EmptyState } from '../../../../shared/ui/EmptyState';
import type { RankingItem } from '../../bias-ranking.types';
import { RankingItemRow } from '../RankingItemRow';
import styles from './RankingBoard.module.css';

export type RankingBoardProps = {
  titleKey: string;
  emptyKey: string;
  category: BiasCategory;
  items: RankingItem[];
};

/**
 * 组装榜单海报内容：以榜别注入的合法三分类 `category` 作偏差信号，取该榜首项（后端已按
 * 分档 / 排序 / TopN 保证顺序）为核心选项，前端只挑选不重算（design D6）。
 * 榜单聚合契约暂无 `data_snapshot_at`，海报仅标注海报生成时间（见交付风险）。
 */
function buildBoardPosterContent(
  titleKey: string,
  category: BiasCategory,
  topItem: RankingItem,
): SharePosterContent {
  return {
    eyebrowKey: titleKey,
    headline: topItem.eventTitle,
    coreOptionName: topItem.optionName,
    biasScore: topItem.biasScore,
    signal: { kind: 'category', category },
  };
}

/**
 * 单榜（bias-ranking，design D6、AC-5）。
 *
 * 标题 + 榜单项列表；该榜为空数组时渲染本地化 `EmptyState`（其余两榜不受影响），
 * 其余情况按后端返回顺序渲染 `RankingItemRow`，前端不重新排序或截取。
 * 榜内有数据时，标题区挂只读分享入口，以该榜展示数据编排出图 + 分发（PRD §4.5、design D6）。
 */
export function RankingBoard({ titleKey, emptyKey, category, items }: RankingBoardProps) {
  const { t } = useTranslation();
  const topItem = items[0];

  return (
    <section className={styles.board}>
      <div className={styles.header}>
        <h2 className={styles.title}>{t(titleKey)}</h2>
        {topItem ? (
          <SharePosterTrigger
            content={buildBoardPosterContent(titleKey, category, topItem)}
            entityName={t(titleKey)}
          />
        ) : null}
      </div>

      {items.length === 0 ? (
        <EmptyState title={t(emptyKey)} />
      ) : (
        <div className={styles.list}>
          {items.map((item) => (
            <RankingItemRow
              key={`${item.eventSlug}-${item.optionName}`}
              item={item}
              category={category}
            />
          ))}
        </div>
      )}
    </section>
  );
}
