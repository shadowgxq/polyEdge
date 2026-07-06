/**
 * 单事件明细的 TanStack Query 封装（single-event-detail，design D2）。
 *
 * 明细服务端态经 `useQuery(['event-detail', slug])` 承载，沿用 `AppProviders`
 * 的 `QueryClient` 快照类默认项；slug 缺失时不发请求（走空态）。
 */

import { useQuery } from '@tanstack/react-query';

import { fetchEventDetail } from './single-event.api';

export const singleEventQueryKeys = {
  detail: (slug: string) => ['event-detail', slug] as const,
};

export function useEventDetailQuery(slug: string | undefined) {
  const normalizedSlug = slug?.trim() ?? '';

  return useQuery({
    queryKey: singleEventQueryKeys.detail(normalizedSlug),
    queryFn: () => fetchEventDetail(normalizedSlug),
    enabled: normalizedSlug.length > 0,
  });
}
