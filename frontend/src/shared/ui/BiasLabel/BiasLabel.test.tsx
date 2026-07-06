import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithI18n } from '../../testing/renderWithI18n';
import { BiasLabel } from './BiasLabel';

describe('BiasLabel', () => {
  it('renders the English label for the hot category', async () => {
    await renderWithI18n(<BiasLabel category="hot" />, 'en');

    expect(screen.getByText('Crowded Attention Signal')).toBeInTheDocument();
  });

  it('renders the Chinese label for the cold category', async () => {
    await renderWithI18n(<BiasLabel category="cold" />, 'zh');

    expect(screen.getByText('低关注·观察信号')).toBeInTheDocument();
  });
});
