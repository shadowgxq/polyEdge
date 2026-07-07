/**
 * 单事件明细数据访问层（single-event-detail，design D2）。
 *
 * 请求经 `shared/api` 的统一 `request`（axios 封装）；组件内不直接发请求。
 * 出参在此边界从 `*Dto`（snake_case）转成 UI domain 类型（camelCase）。
 */

import type { ApiResponseDto } from '../../services/types';
import { request } from '../../shared/api';
import type {
  EventDetail,
  EventDetailDto,
  OptionAnalysis,
  OptionAnalysisDto,
} from './single-event.types';

function toOptionAnalysis(dto: OptionAnalysisDto): OptionAnalysis {
  return {
    name: dto.name,
    iconUrl: dto.icon_url ?? null,
    impliedProbability: dto.price,
    heat: dto.heat,
    biasScore: dto.bias_score,
    label: dto.label,
    excluded: dto.excluded,
    pool: dto.pool ?? null,
    momentum: dto.momentum ?? null,
    fragility: dto.fragility ?? null,
    overheatScore: dto.overheat_score ?? null,
    watchScore: dto.watch_score ?? null,
  };
}

function toEventDetail(dto: EventDetailDto): EventDetail {
  return {
    slug: dto.slug,
    title: dto.title,
    commentCount: dto.comment_count,
    applicable: dto.applicable,
    degradedTradeOnly: dto.degraded_trade_only,
    dataSnapshotAt: dto.data_snapshot_at,
    options: dto.options.map(toOptionAnalysis),
  };
}

export async function fetchEventDetail(slug: string): Promise<EventDetail> {
  const response = await request<ApiResponseDto<EventDetailDto>>({
    method: 'GET',
    url: `/api/v1/events/${encodeURIComponent(slug)}`,
  });

  return toEventDetail(response.data);
}
