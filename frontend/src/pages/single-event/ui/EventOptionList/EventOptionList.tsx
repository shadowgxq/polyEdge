import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { OptionAnalysis } from '../../single-event.types';
import { EventOptionRow } from '../EventOptionRow';
import styles from './EventOptionList.module.css';

/** 展示层排序方向（纯前端重排，不改任一选项数值）。 */
type BiasSortDirection = 'biasDesc' | 'biasAsc';

const SORT_LABEL_KEY = {
  biasDesc: 'detail.sortBiasDesc',
  biasAsc: 'detail.sortBiasAsc',
} as const satisfies Record<BiasSortDirection, string>;

const SORT_DIRECTIONS = ['biasDesc', 'biasAsc'] as const satisfies readonly BiasSortDirection[];

export type EventOptionListProps = {
  options: OptionAnalysis[];
  /** 事件是否适用偏差分析；false 时不提供排序并按原始顺序展示。 */
  applicable: boolean;
};

/**
 * 单事件选项列表区块（single-event-detail，PRD §4.3、AC-3、design D5）。
 *
 * 承载展示层排序（按偏差评分重排，不改任一数值）；被排除选项固定置底且不参与排序，
 * `applicable=false` 时不提供排序。逐项经 `EventOptionRow` 渲染。
 */
export function EventOptionList({ options, applicable }: EventOptionListProps) {
  const { t } = useTranslation();
  const [sortDirection, setSortDirection] = useState<BiasSortDirection>('biasDesc');

  const orderedOptions = useMemo(() => {
    const active = options.filter((option) => !option.excluded);
    const excluded = options.filter((option) => option.excluded);

    const sortedActive =
      applicable
        ? [...active].sort((a, b) =>
            sortDirection === 'biasDesc' ? b.biasScore - a.biasScore : a.biasScore - b.biasScore,
          )
        : active;

    return [...sortedActive, ...excluded];
  }, [options, applicable, sortDirection]);

  return (
    <section className={styles.section} aria-label={t('detail.optionsHeading')}>
      <header className={styles.header}>
        <h2 className={styles.heading}>{t('detail.optionsHeading')}</h2>
        {applicable ? (
          <div className={styles.sort} role="group" aria-label={t('detail.sortLabel')}>
            {SORT_DIRECTIONS.map((direction) => (
              <button
                key={direction}
                type="button"
                className={styles.sortButton}
                aria-pressed={sortDirection === direction}
                onClick={() => setSortDirection(direction)}
              >
                {t(SORT_LABEL_KEY[direction])}
              </button>
            ))}
          </div>
        ) : null}
      </header>

      <ul className={styles.list}>
        {orderedOptions.map((option) => (
          <EventOptionRow key={option.name} option={option} applicable={applicable} />
        ))}
      </ul>
    </section>
  );
}
