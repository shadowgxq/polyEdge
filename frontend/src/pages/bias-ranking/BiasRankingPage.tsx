import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { ErrorState } from '../../shared/ui/ErrorState';
import { useRankingsQuery } from './bias-ranking.queries';
import type { RankingCategory } from './bias-ranking.types';
import { RankingBoards } from './ui/RankingBoards';
import styles from './BiasRankingPage.module.css';

const CATEGORY_PARAM = 'category';

/**
 * 读当前分类（design D4）：优先取 URL `category` 参数作注入点，缺失回落 `hot`。
 * 排行聚合基数是「当前 Tab 默认列表分类」，语义属外壳/列表；本页只消费不新造切换器。
 */
function readCategory(value: string | null): RankingCategory {
  return value === 'world_cup' ? 'world_cup' : 'hot';
}

/**
 * 偏差排行 Tab route entry（bias-ranking，PRD §4.4、AC-4/AC-5/AC-7/AC-9、design D1/D6）。
 *
 * 只承担 composition / 状态归属 / 数据流编排：读当前分类 → `useRankingsQuery`
 * → 按 加载 / 错误 / 成功 分派（加载占位、`ErrorState` 可重试、成功渲染三榜容器）。
 * 三榜与榜单项展示下沉为同模块命名组件。全页只读，无任何交易 / 下单 / 钱包入口。
 */
export function BiasRankingPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  const category = readCategory(searchParams.get(CATEGORY_PARAM));
  const rankingsQuery = useRankingsQuery(category);

  return (
    <section className={styles.page}>
      <h1 className={styles.heading}>{t('nav.ranking')}</h1>

      {rankingsQuery.isPending ? (
        <p className={styles.loading} role="status">
          {t('ranking.loading')}
        </p>
      ) : rankingsQuery.isError ? (
        <ErrorState onRetry={() => void rankingsQuery.refetch()} />
      ) : rankingsQuery.isSuccess ? (
        <RankingBoards boards={rankingsQuery.data} />
      ) : null}
    </section>
  );
}
