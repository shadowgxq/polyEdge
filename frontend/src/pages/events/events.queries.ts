/**
 * 事件列表与输入的 TanStack Query 封装（event-list-and-input，design D2）。
 *
 * - 列表 `useInfiniteQuery`：queryKey 带 `category` 隔离分类缓存，`getNextPageParam` 依 `has_more`。
 * - 名称搜索受控 `useQuery`：`enabled` 依提交动作。
 * - 链接解析 `useMutation`：一次性提交动作，成功后由调用方导航。
 */

import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query';

import { fetchEvents, resolveEvent, searchEvents } from './events.api';
import type { EventCategory, EventResolveResult } from './events.types';

const FIRST_PAGE = 1;

export const eventsQueryKeys = {
  list: (category: EventCategory) => ['events', category] as const,
  search: (q: string) => ['events', 'search', q] as const,
};

export function useEventListQuery(category: EventCategory) {
  return useInfiniteQuery({
    queryKey: eventsQueryKeys.list(category),
    queryFn: ({ pageParam }) => fetchEvents({ category, page: pageParam }),
    initialPageParam: FIRST_PAGE,
    getNextPageParam: (lastPage, _allPages, lastPageParam) =>
      lastPage.hasMore ? lastPageParam + 1 : undefined,
  });
}

export function useEventSearchQuery(q: string, enabled: boolean) {
  const normalizedQuery = q.trim();

  return useQuery({
    queryKey: eventsQueryKeys.search(normalizedQuery),
    queryFn: () => searchEvents({ q: normalizedQuery }),
    enabled: enabled && normalizedQuery.length > 0,
  });
}

export function useResolveEventMutation(options: {
  onSuccess: (result: EventResolveResult) => void;
}) {
  return useMutation({
    mutationFn: (input: string) => resolveEvent(input),
    onSuccess: options.onSuccess,
  });
}
