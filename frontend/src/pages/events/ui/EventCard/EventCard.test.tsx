import { cleanup, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { renderWithI18n } from '../../../../shared/testing/renderWithI18n';
import type { EventCard as EventCardModel } from '../../events.types';
import { EventCard } from './EventCard';

afterEach(cleanup);


const APPLICABLE_EVENT: EventCardModel = {
  slug: 'brazil-to-win-world-cup',
  title: 'Will Brazil win the 2026 World Cup?',
  options: [
    { name: 'Yes', impliedProbability: 0.62 },
    { name: 'No', impliedProbability: 0.38 },
  ],
  optionsTotal: 2,
  overviewLabel: { en: 'Overheated Favorite', zh: '过热热门' },
  overviewOptionName: 'Yes',
  applicable: true,
  dataSnapshotAt: '2026-07-06T08:00:00Z',
};

describe('EventCard', () => {
  it('renders the overview bias label and marks the highest-bias option when applicable', async () => {
    await renderWithI18n(
      <MemoryRouter>
        <EventCard event={APPLICABLE_EVENT} />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByText('Overheated Favorite')).toBeInTheDocument();
    expect(screen.getByText('Largest price–heat gap: Yes')).toBeInTheDocument();
    expect(screen.queryByText('Bias analysis not applicable')).not.toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', '/events/brazil-to-win-world-cup');
  });

  it('marks the card as not applicable and hides the bias label', async () => {
    await renderWithI18n(
      <MemoryRouter>
        <EventCard
          event={{
            ...APPLICABLE_EVENT,
            applicable: false,
            overviewLabel: null,
            overviewOptionName: null,
          }}
        />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByText('Bias analysis not applicable')).toBeInTheDocument();
    expect(screen.queryByText('Overheated Favorite')).not.toBeInTheDocument();
  });

  it('shows a "+N more" hint when the preview omits options', async () => {
    await renderWithI18n(
      <MemoryRouter>
        <EventCard
          event={{
            ...APPLICABLE_EVENT,
            options: [
              { name: 'France', impliedProbability: 0.33 },
              { name: 'Argentina', impliedProbability: 0.17 },
            ],
            optionsTotal: 60,
          }}
        />
      </MemoryRouter>,
      'en',
    );

    expect(screen.getByText('+58 more')).toBeInTheDocument();
  });

  it('omits the "+N more" hint when all options are shown', async () => {
    await renderWithI18n(
      <MemoryRouter>
        <EventCard event={APPLICABLE_EVENT} />
      </MemoryRouter>,
      'en',
    );

    expect(screen.queryByText(/more$/)).not.toBeInTheDocument();
  });
});
