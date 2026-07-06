/**
 * 偏差排行数据访问层（bias-ranking，design D3）。
 *
 * 全部请求经 `shared/api` 的统一 `request`（axios 封装）；组件内不直接发请求。
 * 出参在此边界从 `*Dto`（snake_case）转成 UI domain 类型（camelCase）。
 * `top_n` 不传，随后端默认（前端不写死 TopN，见 design D3）。
 */

import type { ApiResponseDto } from '../../services/types';
import { request } from '../../shared/api';
import type {
  RankingBoards,
  RankingBoardsDto,
  RankingCategory,
  RankingItem,
  RankingItemDto,
} from './bias-ranking.types';

function toRankingItem(dto: RankingItemDto): RankingItem {
  return {
    eventSlug: dto.event_slug,
    eventTitle: dto.event_title,
    optionName: dto.option_name,
    impliedProbability: dto.price,
    biasScore: dto.bias_score,
    label: { zh: dto.label.zh, en: dto.label.en },
  };
}

function toRankingBoards(dto: RankingBoardsDto): RankingBoards {
  return {
    category: dto.category,
    bubble: dto.bubble.map(toRankingItem),
    underhyped: dto.underhyped.map(toRankingItem),
    fair: dto.fair.map(toRankingItem),
  };
}

export type FetchRankingsParams = {
  category: RankingCategory;
};

export async function fetchRankings({ category }: FetchRankingsParams): Promise<RankingBoards> {
  const response = await request<ApiResponseDto<RankingBoardsDto>>({
    method: 'GET',
    url: '/api/v1/rankings',
    params: { category },
  });

  return toRankingBoards(response.data);
}
