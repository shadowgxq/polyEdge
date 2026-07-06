import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithI18n } from '../../testing/renderWithI18n';
import { OptionMetricsRow } from './OptionMetricsRow';

describe('OptionMetricsRow', () => {
  it('renders option name, localized metrics and the bias label', async () => {
    await renderWithI18n(
      <OptionMetricsRow
        optionName="Brazil"
        impliedProbability={0.42}
        heat={1200}
        biasScore={0.35}
        category="hot"
      />,
      'en',
    );

    expect(screen.getByText('Brazil')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
    expect(screen.getByText('+0.35')).toBeInTheDocument();
    expect(screen.getByText('Crowded Attention Signal')).toBeInTheDocument();
  });
});
