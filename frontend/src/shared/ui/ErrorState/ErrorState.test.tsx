import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithI18n } from '../../testing/renderWithI18n';
import { ErrorState } from './ErrorState';

describe('ErrorState', () => {
  it('renders default localized copy and fires the retry callback', async () => {
    const user = userEvent.setup();
    const handleRetry = vi.fn();
    await renderWithI18n(<ErrorState onRetry={handleRetry} />, 'en');

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
