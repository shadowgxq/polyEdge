/**
 * 事件列表与输入模块类型（event-list-and-input，PRD §4.1/§4.2）。
 *
 * `*Dto` 为后端线上契约（snake_case，对齐 analysis-api tasks §6 冻结契约），
 * 仅在 `events.api.ts` 边界出现；UI 只消费转换后的 domain 类型（camelCase）。
 */

import type { IsoDateTimeString } from '../../services/types';

/** 事件分类（默认落 `hot`）。 */
export type EventCategory = 'hot' | 'world_cup';

/** 搜索命中范围：上游搜索 / 本地缓存模糊回退。 */
export type EventSearchScope = 'upstream' | 'local_cache';

/* ------------------------------------------------------------------ *
 * 后端契约 DTO（snake_case）
 * ------------------------------------------------------------------ */

export type EventOptionDto = {
  name: string;
  /** 选项价格，0..1 区间即隐含概率。 */
  price: number;
};

/** 概览偏差标签的本地化文案（后端已算好三分类文案，前端不自算偏差）。 */
export type EventOverviewLabelDto = {
  zh: string;
  en: string;
};

export type EventCardDto = {
  slug: string;
  title: string;
  options: EventOptionDto[];
  /** 该事件选项总数（options 仅为按概率降序的 TopN 预览子集）。 */
  options_total: number;
  overview_label: EventOverviewLabelDto | null;
  overview_option_name: string | null;
  applicable: boolean;
  data_snapshot_at: IsoDateTimeString;
};

export type EventListDataDto = {
  category: EventCategory;
  items: EventCardDto[];
  has_more: boolean;
};

export type EventSearchCandidateDto = {
  slug: string;
  title: string;
};

export type EventSearchDataDto = {
  candidates: EventSearchCandidateDto[];
  search_scope: EventSearchScope;
};

/**
 * `POST /api/v1/events/resolve` 返回完整 `EventDetail`，本 change 仅取 `slug` 做导航，
 * 故只声明用到的子集（明细正文契约归 single-event-detail 消费）。
 */
export type EventResolveDataDto = {
  slug: string;
};

/* ------------------------------------------------------------------ *
 * UI domain 类型（camelCase）
 * ------------------------------------------------------------------ */

export type EventOption = {
  name: string;
  /** 隐含概率，0..1 区间。 */
  impliedProbability: number;
};

export type EventOverviewLabel = {
  zh: string;
  en: string;
};

export type EventCard = {
  slug: string;
  title: string;
  /** 按概率降序的 TopN 选项预览。 */
  options: EventOption[];
  /** 该事件选项总数，> options.length 时前端提示「+N 更多」。 */
  optionsTotal: number;
  /** 概览偏差标签本地化文案；`applicable=false` 时为 null。 */
  overviewLabel: EventOverviewLabel | null;
  /** 概览标签对应的最大偏差选项名；`applicable=false` 时为 null。 */
  overviewOptionName: string | null;
  applicable: boolean;
  dataSnapshotAt: IsoDateTimeString;
};

export type EventListData = {
  category: EventCategory;
  items: EventCard[];
  hasMore: boolean;
};

export type EventSearchCandidate = {
  slug: string;
  title: string;
};

export type EventSearchData = {
  candidates: EventSearchCandidate[];
  searchScope: EventSearchScope;
};

export type EventResolveResult = {
  slug: string;
};
