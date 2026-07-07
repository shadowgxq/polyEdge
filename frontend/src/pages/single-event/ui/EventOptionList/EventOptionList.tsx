import { useTranslation } from 'react-i18next';

import type { OptionAnalysis } from '../../single-event.types';
import { EventOptionRow } from '../EventOptionRow';
import type { BiasSortDirection } from './biasSort';
import styles from './EventOptionList.module.css';
import { LabelTipPopover } from './LabelTipPopover';

const SORT_LABEL_KEY = {
  biasDesc: 'detail.sortBiasDesc',
  biasAsc: 'detail.sortBiasAsc',
} as const satisfies Record<BiasSortDirection, string>;

const SORT_DIRECTIONS = ['biasDesc', 'biasAsc'] as const satisfies readonly BiasSortDirection[];

export type EventOptionListProps = {
  /** 已由页面按 `sortDirection` 排好序的可见选项（展示顺序即入参顺序）。 */
  options: OptionAnalysis[];
  /** 事件是否适用偏差分析；false 时不提供排序并按原始顺序展示。 */
  applicable: boolean;
  /** 当前排序方向（状态归属页面，分享海报与本列表共用同一来源）。 */
  sortDirection: BiasSortDirection;
  /** 切换排序方向。 */
  onSortChange: (direction: BiasSortDirection) => void;
};

/**
 * 单事件选项列表区块（single-event-detail，PRD §4.3、AC-3、design D5）。
 *
 * 承载展示层排序的 UI；排序方向与排好序的数据由页面注入（单一来源），
 * `excluded=true` 的选项在进入本组件前已被过滤，`applicable=false` 时不提供排序。
 * 逐项经 `EventOptionRow` 渲染。
 */
export function EventOptionList({
  options,
  applicable,
  sortDirection,
  onSortChange,
}: EventOptionListProps) {
  const { t } = useTranslation();

  return (
    <section className={styles.section} aria-label={t('detail.optionsHeading')}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h2 className={styles.heading}>{t('detail.optionsHeading')}</h2>
          {applicable ? <LabelTipPopover /> : null}
        </div>
        {applicable ? (
          <div className={styles.sort} role="group" aria-label={t('detail.sortLabel')}>
            {SORT_DIRECTIONS.map((direction) => (
              <button
                key={direction}
                type="button"
                className={styles.sortButton}
                aria-pressed={sortDirection === direction}
                onClick={() => onSortChange(direction)}
              >
                {t(SORT_LABEL_KEY[direction])}
              </button>
            ))}
          </div>
        ) : null}
      </header>

      <ul className={styles.list}>
        <li
          className={applicable ? styles.tableHeader : styles.rawTableHeader}
          aria-hidden="true"
        >
          <span>{t('detail.optionColumn')}</span>
          <span>{t('metrics.impliedProbability')}</span>
          <span>{t('metrics.heat')}</span>
          {applicable ? (
            <>
              <span>{t('metrics.biasScore')}</span>
              <span>{t('detail.signalColumn')}</span>
            </>
          ) : null}
        </li>
        {options.map((option) => (
          <EventOptionRow key={option.name} option={option} applicable={applicable} />
        ))}
      </ul>
    </section>
  );
}
