import clsx from 'clsx';
import { useTranslation } from 'react-i18next';

import type { EventCategory } from '../../events.types';
import styles from './EventCategoryTabs.module.css';

const CATEGORY_TABS = [
  { category: 'hot', labelKey: 'events.category.hot' },
  { category: 'world_cup', labelKey: 'events.category.worldCup' },
] as const satisfies readonly { category: EventCategory; labelKey: string }[];

export type EventCategoryTabsProps = {
  category: EventCategory;
  onCategoryChange: (category: EventCategory) => void;
};

/**
 * 分类分段控件（PRD §4.1、design D6）。
 * 热门 / 世界杯两分类，窄屏用分段控件不横向溢出；切换驱动列表 `useInfiniteQuery`。
 */
export function EventCategoryTabs({ category, onCategoryChange }: EventCategoryTabsProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.tabs} role="group" aria-label={t('events.category.label')}>
      {CATEGORY_TABS.map((tab) => {
        const isActive = tab.category === category;

        return (
          <button
            key={tab.category}
            type="button"
            className={clsx(styles.tab, isActive && styles.active)}
            aria-pressed={isActive}
            onClick={() => onCategoryChange(tab.category)}
          >
            {t(tab.labelKey)}
          </button>
        );
      })}
    </div>
  );
}
