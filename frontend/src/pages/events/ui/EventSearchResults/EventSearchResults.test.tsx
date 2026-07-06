import { cleanup, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { renderWithI18n } from '../../../../shared/testing/renderWithI18n';
import type { EventSearchCandidate } from '../../events.types';
import { EventSearchResults } from './EventSearchResults';

afterEach(cleanup);

const CANDIDATES: EventSearchCandidate[] = [
  { slug: 'event-a', title: 'Event A' },
  { slug: 'event-b', title: 'Event B' },
];

const noop = () => {};

describe('EventSearchResults', () => {
  it('annotates the local cache fallback scope above candidates', async () => {
    await renderWithI18n(
      <MemoryRouter>
        <EventSearchResults
          status="success"
          candidates={CANDIDATES}
          searchScope="local_cache"
          onRetry={noop}
        />
      </MemoryRouter>,
      'en',
    );

    expect(
      screen.getByText('Searching only within currently indexed events.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Event A' })).toHaveAttribute(
      'href',
      '/events/event-a',
    );
  });

  it('shows an empty state with retry guidance when no candidates match', async () => {
    await renderWithI18n(
      <MemoryRouter>
        <EventSearchResults status="success" candidates={[]} searchScope="upstream" onRetry={noop} />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByText('No matching events')).toBeInTheDocument();
    expect(screen.getByText('Try a different name.')).toBeInTheDocument();
  });
});
