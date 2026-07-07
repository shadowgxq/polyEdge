import { cleanup, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithI18n } from '../../../../shared/testing/renderWithI18n';
import type { EventCard as EventCardModel } from '../../events.types';
import { EventCardList } from './EventCardList';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const EVENT: EventCardModel = {
  slug: 'event-one',
  title: 'Event one',
  options: [{ name: 'Yes', impliedProbability: 0.5 }],
  optionsTotal: 1,
  overviewLabel: null,
  overviewOptionName: null,
  applicable: false,
  dataSnapshotAt: '2026-07-06T08:00:00Z',
};

const noop = () => {};

describe('EventCardList', () => {
  it('shows the load more entry only when there are more pages', async () => {
    const { rerender } = await renderWithI18n(
      <MemoryRouter>
        <EventCardList
          events={[EVENT]}
          totalCount={2}
          status="success"
          category="hot"
          hasNextPage
          isFetchingNextPage={false}
          onLoadMore={noop}
          onRetry={noop}
          onSwitchToHot={noop}
        />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByRole('button', { name: 'Load more' })).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <EventCardList
          events={[EVENT]}
          totalCount={1}
          status="success"
          category="hot"
          hasNextPage={false}
          isFetchingNextPage={false}
          onLoadMore={noop}
          onRetry={noop}
          onSwitchToHot={noop}
        />
      </MemoryRouter>,
    );

    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument();
    expect(screen.getByText('All currently indexed events are shown')).toBeInTheDocument();
  });

  it('auto-loads the next page when the sentinel enters view', async () => {
    const onLoadMore = vi.fn();

    class ImmediateIntersectionObserver implements IntersectionObserver {
      readonly root = null;
      readonly rootMargin = '';
      readonly thresholds = [];

      constructor(private readonly callback: IntersectionObserverCallback) {}

      disconnect = vi.fn(() => {});
      observe = vi.fn(() => {
        this.callback([{ isIntersecting: true } as IntersectionObserverEntry], this);
      });
      takeRecords = vi.fn((): IntersectionObserverEntry[] => []);
      unobserve = vi.fn(() => {});
    }

    vi.stubGlobal('IntersectionObserver', ImmediateIntersectionObserver);

    await renderWithI18n(
      <MemoryRouter>
        <EventCardList
          events={[EVENT]}
          totalCount={3}
          status="success"
          category="hot"
          hasNextPage
          isFetchingNextPage={false}
          onLoadMore={onLoadMore}
          onRetry={noop}
          onSwitchToHot={noop}
        />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByText('1 / 3 currently indexed events shown')).toBeInTheDocument();
    expect(screen.getByText('Keep scrolling to load more')).toBeInTheDocument();
    await waitFor(() => expect(onLoadMore).toHaveBeenCalledTimes(1));
  });

  it('offers a switch-to-hot action when the world cup category is empty', async () => {
    const onSwitchToHot = vi.fn();
    await renderWithI18n(
      <MemoryRouter>
        <EventCardList
          events={[]}
          totalCount={0}
          status="success"
          category="world_cup"
          hasNextPage={false}
          isFetchingNextPage={false}
          onLoadMore={noop}
          onRetry={noop}
          onSwitchToHot={onSwitchToHot}
        />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByText('No World Cup events right now')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to Hot' })).toBeInTheDocument();
  });
});
