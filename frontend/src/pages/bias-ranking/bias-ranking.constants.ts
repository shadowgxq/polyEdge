import type { BiasCategory } from '../../shared/ui/BiasLabel';
import type { RankingBoardKey } from './bias-ranking.types';

/**
 * 三榜元数据（bias-multi-signal）：榜键 → 信号色档 + i18n 文案 key。
 *
 * 榜别诚实语义：bubble → 过热榜（hot tone）、underhyped → 观察榜（cold tone）、
 * fair → 合理（fair tone）。DTO 字段名沿用 bubble/underhyped/fair。
 * 行信号色走 `category` tone + `tokens.css`；标签文案取后端各项 `label`，前端不重算分类。
 */
export const RANKING_BOARDS = [
  {
    key: 'bubble',
    category: 'hot',
    titleKey: 'ranking.board.bubble.title',
    emptyKey: 'ranking.board.bubble.empty',
  },
  {
    key: 'underhyped',
    category: 'cold',
    titleKey: 'ranking.board.underhyped.title',
    emptyKey: 'ranking.board.underhyped.empty',
  },
  {
    key: 'fair',
    category: 'fair',
    titleKey: 'ranking.board.fair.title',
    emptyKey: 'ranking.board.fair.empty',
  },
] as const satisfies readonly {
  key: RankingBoardKey;
  category: BiasCategory;
  titleKey: string;
  emptyKey: string;
}[];
