import { useTranslation } from 'react-i18next';

import { EmptyState } from '../../../../shared/ui/EmptyState';
import { ErrorState } from '../../../../shared/ui/ErrorState';
import type { EventCard as EventCardModel, EventCategory } from '../../events.types';
import { EventCard } from '../EventCard';
import styles from './EventCardList.module.css';

export type EventCardListProps = {
  events: EventCardModel[];
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
  status,
  category,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  onRetry,
  onSwitchToHot,
}: EventCardListProps) {
  const { t } = useTranslation();

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
    <div className={styles.list}>
      {events.map((event) => (
        <EventCard key={event.slug} event={event} />
      ))}

      {hasNextPage ? (
        <button
          type="button"
          className={styles.loadMore}
          onClick={onLoadMore}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? t('events.list.loadingMore') : t('events.list.loadMore')}
        </button>
      ) : null}
    </div>
  );
}
