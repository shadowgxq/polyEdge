import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { App } from './App';

// 排行 Tab 现由真实 bias-ranking 页承载，mock 其数据访问层，避免依赖真实网络，
// 并提供一条回跳 `/events/sample-event` 的榜单项以覆盖「榜单回跳」流程。
vi.mock('../pages/bias-ranking/bias-ranking.api', () => ({
  fetchRankings: vi.fn(async () => ({
    category: 'hot',
    bubble: [
      {
        eventSlug: 'sample-event',
        eventTitle: 'Sample Event',
        optionName: 'Yes',
        impliedProbability: 0.82,
        biasScore: 1.2,
        label: { zh: '高热度·泡沫风险', en: 'Overheated · Bubble Risk' },
      },
    ],
    underhyped: [],
    fair: [],
  })),
}));

describe('App shell routing', () => {
  it('defaults to the event list, switches tabs, supports 榜单回跳 and breadcrumb返回', async () => {
    const user = userEvent.setup();
    render(<App />);

    // 默认落事件列表
    expect(screen.getByRole('heading', { level: 1, name: 'Events' })).toBeInTheDocument();

    // 切换到偏差排行 Tab
    await user.click(screen.getByRole('link', { name: 'Bias Ranking' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Bias Ranking' })).toBeInTheDocument();

    // 榜单项 → 单事件明细回跳（榜单项行 aria-label 经 i18n 插值）
    const rankingRow = await screen.findByRole('link', {
      name: 'View Sample Event · Yes details',
    });
    await user.click(rankingRow);
    expect(screen.getByText('sample-event')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument();

    // 明细面包屑返回来源列表
    const breadcrumb = screen.getByRole('navigation', { name: 'Events' });
    await user.click(within(breadcrumb).getByRole('link', { name: 'Events' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Events' })).toBeInTheDocument();
  });
});
