import { cleanup, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithI18n } from '../../../../shared/testing/renderWithI18n';
import type { EventCard as EventCardModel } from '../../events.types';
import { EventCardList } from './EventCardList';

afterEach(cleanup);

const EVENT: EventCardModel = {
  slug: 'event-one',
  title: 'Event one',
  options: [{ name: 'Yes', impliedProbability: 0.5 }],
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
  });

  it('offers a switch-to-hot action when the world cup category is empty', async () => {
    const onSwitchToHot = vi.fn();
    await renderWithI18n(
      <MemoryRouter>
        <EventCardList
          events={[]}
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
