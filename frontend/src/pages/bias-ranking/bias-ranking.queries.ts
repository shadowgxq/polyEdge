/**
 * 偏差排行的 TanStack Query 封装（bias-ranking，design D3）。
 *
 * queryKey 带 `category` 隔离分类缓存；沿用外壳 `QueryClient` 默认项。
 * 偏差结果属服务端快照态，仅经 Query 承载，组件内不直接发请求。
 */

import { useQuery } from '@tanstack/react-query';

import { fetchRankings } from './bias-ranking.api';
import type { RankingCategory } from './bias-ranking.types';

export const rankingsQueryKeys = {
  boards: (category: RankingCategory) => ['rankings', category] as const,
};

export function useRankingsQuery(category: RankingCategory) {
  return useQuery({
    queryKey: rankingsQueryKeys.boards(category),
    queryFn: () => fetchRankings({ category }),
  });
}
