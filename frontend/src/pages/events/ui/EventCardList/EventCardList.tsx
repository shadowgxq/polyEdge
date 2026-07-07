import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '../../../../shared/ui/EmptyState';
import { ErrorState } from '../../../../shared/ui/ErrorState';
import type { EventCard as EventCardModel, EventCategory } from '../../events.types';
import { EventCard } from '../EventCard';
import styles from './EventCardList.module.css';

export type EventCardListProps = {
  events: EventCardModel[];
  totalCount: number;
  status: 'pending' | 'error' | 'success';
  category: EventCategory;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
  onRetry: () => void;
  onSwitchToHot: () => void;
};

/**
 * 事件卡片列表（PRD §4.1、AC-1/AC-5、design D5）。
 * 承载加载 / 错误 / 空 / 成功四态与「加载更多」入口；不表现为空白。
 */
export function EventCardList({
  events,
  totalCount,
  status,
  category,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  onRetry,
  onSwitchToHot,
}: EventCardListProps) {
  const { t } = useTranslation();
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (
      !sentinel ||
      !hasNextPage ||
      isFetchingNextPage ||
      typeof IntersectionObserver === 'undefined'
    ) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          onLoadMore();
        }
      },
      { rootMargin: '360px 0px' },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, onLoadMore]);

  if (status === 'pending') {
    return (
      <p className={styles.loading} role="status">
        {t('events.list.loading')}
      </p>
    );
  }

  if (status === 'error') {
    return <ErrorState onRetry={onRetry} />;
  }

  if (events.length === 0) {
    if (category === 'world_cup') {
      return (
        <EmptyState
          title={t('events.list.worldCupEmpty')}
          action={
            <button type="button" className={styles.switch} onClick={onSwitchToHot}>
              {t('events.list.switchToHot')}
            </button>
          }
        />
      );
    }

    return <EmptyState title={t('events.list.empty')} />;
  }

  return (
    <section className={styles.results} aria-label={t('events.list.resultsLabel')}>
      <div className={styles.summary}>
        <span>{t('events.list.loadedCount', { shown: events.length, total: totalCount })}</span>
      </div>

      <div className={styles.list}>
        {events.map((event) => (
          <EventCard key={event.slug} event={event} />
        ))}
      </div>

      {hasNextPage ? (
        <div ref={sentinelRef} className={styles.sentinel}>
          <span className={styles.loadingMore} role={isFetchingNextPage ? 'status' : undefined}>
            {isFetchingNextPage ? t('events.list.loadingMore') : t('events.list.scrollForMore')}
          </span>
          <button
            type="button"
            className={styles.loadMore}
            onClick={onLoadMore}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? t('events.list.loadingMore') : t('events.list.loadMore')}
          </button>
        </div>
      ) : (
        <p className={styles.end}>{t('events.list.end')}</p>
      )}
    </section>
  );
}
