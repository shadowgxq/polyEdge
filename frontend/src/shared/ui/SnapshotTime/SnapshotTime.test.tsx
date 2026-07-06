import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithI18n } from '../../testing/renderWithI18n';
import { SnapshotTime } from './SnapshotTime';

describe('SnapshotTime', () => {
  it('renders a localized data snapshot label', async () => {
    await renderWithI18n(<SnapshotTime snapshotAt="2026-07-06T10:00:00.000Z" />, 'en');

    const node = screen.getByText(/Data snapshot:/);
    expect(node).toBeInTheDocument();
    expect(node).toHaveAttribute('dateTime', '2026-07-06T10:00:00.000Z');
  });

  it('renders nothing for an invalid snapshot time', async () => {
    const { container } = await renderWithI18n(<SnapshotTime snapshotAt="not-a-date" />, 'en');

    expect(container).toBeEmptyDOMElement();
  });
});
