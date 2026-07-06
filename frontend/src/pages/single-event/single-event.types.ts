/**
 * 单事件明细模块类型（single-event-detail，PRD §4.3）。
 *
 * `*Dto` 为后端线上契约（snake_case，对齐 analysis-api `GET /api/v1/events/{slug}` 冻结契约），
 * 仅在 `single-event.api.ts` 边界出现；UI 只消费转换后的 domain 类型（camelCase）。
 *
 * 说明：`OptionAnalysis.label` 为后端已本地化文案（`{zh,en}`），不含 `BiasLabel` 所需的
 * `category`（'hot'|'cold'|'fair'）枚举。前端不重算偏差分类，直接渲染该文案（详见 UI 层兜底）。
 */

import type { IsoDateTimeString } from '../../services/types';

/** 选项偏差三分类的本地化文案（后端已算好，前端不自算偏差）。 */
export type OptionBiasLabelText = {
  zh: string;
  en: string;
};

/* ------------------------------------------------------------------ *
 * 后端契约 DTO（snake_case）
 * ------------------------------------------------------------------ */

export type OptionAnalysisDto = {
  name: string;
  /** 选项价格，0..1 区间即隐含概率。 */
  price: number;
  /** 热度指标，口径由后端决定。 */
  heat: number;
  /** 偏差评分，后端算好；前端只展示不重算。 */
  bias_score: number;
  /** 偏差三分类本地化文案；被排除 / 不适用时为 null。 */
  label: OptionBiasLabelText | null;
  /** 价格全为 0 或数据缺失被排除出偏差计算。 */
  excluded: boolean;
};

export type EventDetailDto = {
  slug: string;
  title: string;
  /** 事件级关注度（评论数），不参与单选项偏差。 */
  comment_count: number;
  /** 是否适用偏差分析；false 时仅展示原始选项数据。 */
  applicable: boolean;
  /** 全事件退化为纯交易热度标注。 */
  degraded_trade_only: boolean;
  data_snapshot_at: IsoDateTimeString;
  options: OptionAnalysisDto[];
};

/* ------------------------------------------------------------------ *
 * UI domain 类型（camelCase）
 * ------------------------------------------------------------------ */

export type OptionAnalysis = {
  name: string;
  /** 隐含概率，0..1 区间。 */
  impliedProbability: number;
  heat: number;
  biasScore: number;
  /** 偏差三分类本地化文案；被排除 / 不适用时为 null。 */
  label: OptionBiasLabelText | null;
  excluded: boolean;
};

export type EventDetail = {
  slug: string;
  title: string;
  commentCount: number;
  applicable: boolean;
  degradedTradeOnly: boolean;
  dataSnapshotAt: IsoDateTimeString;
  options: OptionAnalysis[];
};
