/**
 * 事件列表与输入数据访问层（event-list-and-input，design D2/D3）。
 *
 * 全部请求经 `shared/api` 的统一 `request`（axios 封装）；组件内不直接发请求。
 * 出参在此边界从 `*Dto`（snake_case）转成 UI domain 类型（camelCase）。
 */

import type { ApiResponseDto } from '../../services/types';
import { normalizeApiError, request } from '../../shared/api';
import type {
  EventCard,
  EventCardDto,
  EventCategory,
  EventListData,
  EventListDataDto,
  EventOption,
  EventOptionDto,
  EventResolveDataDto,
  EventResolveResult,
  EventSearchData,
  EventSearchDataDto,
} from './events.types';

function toEventOption(dto: EventOptionDto): EventOption {
  return { name: dto.name, impliedProbability: dto.price };
}

function toEventCard(dto: EventCardDto): EventCard {
  return {
    slug: dto.slug,
    title: dto.title,
    options: dto.options.map(toEventOption),
    overviewLabel: dto.overview_label,
    overviewOptionName: dto.overview_option_name,
    applicable: dto.applicable,
    dataSnapshotAt: dto.data_snapshot_at,
  };
}

function toEventListData(dto: EventListDataDto): EventListData {
  return {
    category: dto.category,
    items: dto.items.map(toEventCard),
    hasMore: dto.has_more,
  };
}

function toEventSearchData(dto: EventSearchDataDto): EventSearchData {
  return {
    candidates: dto.candidates.map((candidate) => ({
      slug: candidate.slug,
      title: candidate.title,
    })),
    searchScope: dto.search_scope,
  };
}

export type FetchEventsParams = {
  category: EventCategory;
  page: number;
  /** 省略时随后端默认上限（design Open Questions：前端不写死 page_size）。 */
  pageSize?: number;
};

export async function fetchEvents({
  category,
  page,
  pageSize,
}: FetchEventsParams): Promise<EventListData> {
  const response = await request<ApiResponseDto<EventListDataDto>>({
    method: 'GET',
    url: '/api/v1/events',
    params: { category, page, page_size: pageSize },
  });

  return toEventListData(response.data);
}

export async function resolveEvent(input: string): Promise<EventResolveResult> {
  const response = await request<ApiResponseDto<EventResolveDataDto | null>>({
    method: 'POST',
    url: '/api/v1/events/resolve',
    data: { input },
  });

  const slug = response.data?.slug;
  if (!slug) {
    // 后端以 code=0 但空 data 表达「未找到」时，归一为错误态走 mutation onError → 空态引导。
    throw normalizeApiError(new Error('Event not found'));
  }

  return { slug };
}

export type SearchEventsParams = {
  q: string;
  /** 省略时随后端默认 limit。 */
  limit?: number;
};

export async function searchEvents({ q, limit }: SearchEventsParams): Promise<EventSearchData> {
  const response = await request<ApiResponseDto<EventSearchDataDto>>({
    method: 'GET',
    url: '/api/v1/events/search',
    params: { q, limit },
  });

  return toEventSearchData(response.data);
}
