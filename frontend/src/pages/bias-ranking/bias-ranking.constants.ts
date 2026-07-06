import type { BiasCategory } from '../../shared/ui/BiasLabel';
import type { RankingBoardKey } from './bias-ranking.types';

/**
 * 三榜元数据（design D2）：榜键 → 偏差三分类 + i18n 文案 key。
 *
 * 榜别与三分类一一对应（后端已按分类分好组，此映射为版块级三分类）：
 *   bubble → hot（泡沫风险）、underhyped → cold（冷门机会）、fair → fair（合理）。
 * 偏差信号色与文案统一走 `BiasLabel` 基元 + `tokens.css`，前端不重算分类。
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
