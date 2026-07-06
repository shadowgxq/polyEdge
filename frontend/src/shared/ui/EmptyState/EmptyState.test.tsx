import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithI18n } from '../../testing/renderWithI18n';
import { EmptyState } from './EmptyState';

describe('EmptyState', () => {
  it('renders title, description and an optional action', async () => {
    await renderWithI18n(
      <EmptyState
        title="No matched events"
        description="Try switching back to the hot tab."
        action={<button type="button">Switch tab</button>}
      />,
      'en',
    );

    expect(screen.getByText('No matched events')).toBeInTheDocument();
    expect(screen.getByText('Try switching back to the hot tab.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Switch tab' })).toBeInTheDocument();
  });
});
