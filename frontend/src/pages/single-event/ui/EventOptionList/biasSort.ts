/**
 * 单事件选项列表的展示层排序口径（single-event-detail，PRD §4.3、design D5）。
 *
 * 纯前端重排，不改任一选项数值。列表与分享海报共用此口径，
 * 从而保证「分享的核心选项 ＝ 当前列表第一行」。
 */

import type { OptionAnalysis } from '../../single-event.types';

/** 展示层排序方向。 */
export type BiasSortDirection = 'biasDesc' | 'biasAsc';

/** 列表与分享海报共用的默认排序方向。 */
export const DEFAULT_BIAS_SORT_DIRECTION: BiasSortDirection = 'biasDesc';

/**
 * 按偏差评分对可见选项做展示层排序（纯函数，不改任一数值）。
 * `applicable=false` 时保留原始顺序。
 */
export function sortOptionsByBias(
  options: OptionAnalysis[],
  direction: BiasSortDirection,
  applicable: boolean,
): OptionAnalysis[] {
  if (!applicable) {
    return options;
  }
  return [...options].sort((a, b) =>
    direction === 'biasDesc' ? b.biasScore - a.biasScore : a.biasScore - b.biasScore,
  );
}
