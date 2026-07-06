import clsx from 'clsx';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { RANKING_BOARDS } from '../../bias-ranking.constants';
import type { RankingBoardKey, RankingBoards as RankingBoardsModel } from '../../bias-ranking.types';
import { RankingBoard } from '../RankingBoard';
import styles from './RankingBoards.module.css';

export type RankingBoardsProps = {
  boards: RankingBoardsModel;
};

/**
 * 三榜容器（bias-ranking，design D5、AC-9）。
 *
 * 宽屏三榜横向并列分区；≤430px 窄屏改为三榜分段 Tab（bubble/underhyped/fair 三段）
 * + 单榜卡片纵向排列，避免横向溢出。分段激活段为组件内本地 UI 态（非路由态）。
 * 布局仅用 `tokens.css` token；宽窄两态复用同一 `RankingBoard`，仅容器切布局。
 */
export function RankingBoards({ boards }: RankingBoardsProps) {
  const { t } = useTranslation();
  const [activeBoardKey, setActiveBoardKey] = useState<RankingBoardKey>(RANKING_BOARDS[0].key);

  return (
    <div className={styles.root}>
      <div className={styles.segments} role="group" aria-label={t('ranking.board.label')}>
        {RANKING_BOARDS.map((board) => {
          const isActive = board.key === activeBoardKey;

          return (
            <button
              key={board.key}
              type="button"
              className={clsx(styles.segment, isActive && styles.segmentActive)}
              aria-pressed={isActive}
              onClick={() => setActiveBoardKey(board.key)}
            >
              {t(board.titleKey)}
            </button>
          );
        })}
      </div>

      <div className={styles.columns}>
        {RANKING_BOARDS.map((board) => (
          <div
            key={board.key}
            className={clsx(styles.column, board.key === activeBoardKey && styles.columnActive)}
          >
            <RankingBoard
              titleKey={board.titleKey}
              emptyKey={board.emptyKey}
              category={board.category}
              items={boards[board.key]}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
