import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

import type { EventCategory, EventResolveResult } from './events.types';
import { useEventListQuery } from './events.queries';
import { EventCardList } from './ui/EventCardList';
import { EventCategoryTabs } from './ui/EventCategoryTabs';
import { EventInputPanel } from './ui/EventInputPanel';
import styles from './EventsPage.module.css';

const CATEGORY_PARAM = 'category';

function readCategory(value: string | null): EventCategory {
  return value === 'world_cup' ? 'world_cup' : 'hot';
}

/**
 * 事件列表与输入页 route entry（PRD §4.1/§4.2、design D1）。
 * 只承担分类 Tab 状态归属（走 URL 参数）、列表数据流编排与导航副作用；
 * 独立 UI 区块下沉为同模块命名组件。
 */
export function EventsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const category = readCategory(searchParams.get(CATEGORY_PARAM));
  const listQuery = useEventListQuery(category);
  const events = listQuery.data?.pages.flatMap((page) => page.items) ?? [];

  const handleCategoryChange = (next: EventCategory) => {
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev);
        if (next === 'hot') {
          params.delete(CATEGORY_PARAM);
        } else {
          params.set(CATEGORY_PARAM, next);
        }
        return params;
      },
      { replace: true },
    );
  };

  const navigateToEvent = (result: EventResolveResult) => {
    navigate(`/events/${result.slug}`);
  };

  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.heading}>{t('nav.eventList')}</h1>
        <p className={styles.subtitle}>{t('events.subtitle')}</p>
      </header>

      <EventInputPanel onResolved={navigateToEvent} />

      <EventCategoryTabs category={category} onCategoryChange={handleCategoryChange} />

      <EventCardList
        events={events}
        status={listQuery.status}
        category={category}
        hasNextPage={listQuery.hasNextPage}
        isFetchingNextPage={listQuery.isFetchingNextPage}
        onLoadMore={() => void listQuery.fetchNextPage()}
        onRetry={() => void listQuery.refetch()}
        onSwitchToHot={() => handleCategoryChange('hot')}
      />
    </section>
  );
}
