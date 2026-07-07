import { cleanup, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithI18n } from '../../../../shared/testing/renderWithI18n';
import type { OptionAnalysis } from '../../single-event.types';
import { EventOptionList } from './EventOptionList';

beforeEach(() => {
  class ResizeObserverMock implements ResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }

  vi.stubGlobal('ResizeObserver', ResizeObserverMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const OPTION: OptionAnalysis = {
  name: 'Brazil',
  impliedProbability: 0.42,
  heat: 0.36,
  biasScore: 12,
  label: { zh: '共识热门', en: 'Consensus Favorite' },
  excluded: false,
};

describe('EventOptionList', () => {
  it('shows a subtle label explanation popover on demand', async () => {
    const user = userEvent.setup();

    await renderWithI18n(
      <EventOptionList
        options={[OPTION]}
        applicable
        sortDirection="biasDesc"
        onSortChange={() => {}}
      />,
      'zh',
    );

    await user.click(screen.getByRole('button', { name: '查看标签说明' }));

    expect(screen.getByText('标签怎么读')).toBeInTheDocument();
    expect(screen.getByText('这些标签只描述当前快照里的价格位置与关注结构，不代表交易建议。')).toBeInTheDocument();
    expect(screen.getByText('被炒作冷门')).toBeInTheDocument();
  });
});
