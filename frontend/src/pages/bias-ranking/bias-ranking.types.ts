/**
 * 偏差排行模块类型（bias-ranking，PRD §4.4、design D3）。
 *
 * `*Dto` 为后端线上契约（snake_case，对齐 analysis-api `GET /api/v1/rankings`），
 * 仅在 `bias-ranking.api.ts` 边界出现；UI 只消费转换后的 domain 类型（camelCase）。
 * 排行的分档 / 排序 / TopN 截取全由后端保证，前端不重算。
 */

/** 排行分类（默认落 `hot`），语义沿用外壳/列表既定分类。 */
export type RankingCategory = 'hot' | 'world_cup';

/** 三榜键：泡沫风险 / 冷门机会 / 合理。 */
export type RankingBoardKey = 'bubble' | 'underhyped' | 'fair';

/* ------------------------------------------------------------------ *
 * 后端契约 DTO（snake_case）
 * ------------------------------------------------------------------ */

/** 后端已本地化的偏差文案（`{zh,en}`），不含 `BiasLabel` 所需的 category 枚举。 */
export type RankingLabelDto = {
  zh: string;
  en: string;
};

export type RankingItemDto = {
  event_slug: string;
  event_title: string;
  option_name: string;
  /** 选项价格，0..1 区间即隐含概率。 */
  price: number;
  bias_score: number;
  label: RankingLabelDto;
};

export type RankingBoardsDto = {
  category: RankingCategory;
  bubble: RankingItemDto[];
  underhyped: RankingItemDto[];
  fair: RankingItemDto[];
};

/* ------------------------------------------------------------------ *
 * UI domain 类型（camelCase）
 * ------------------------------------------------------------------ */

export type RankingLabel = {
  zh: string;
  en: string;
};

export type RankingItem = {
  eventSlug: string;
  eventTitle: string;
  optionName: string;
  /** 隐含概率，0..1 区间（后端 `price`）。 */
  impliedProbability: number;
  biasScore: number;
  /**
   * 后端已本地化偏差文案，不含 category 枚举；仅备用。
   * 渲染唯一来源是「榜别 → BiasCategory」映射经 `BiasLabel` 基元（design D2），
   * 不以此文案反推分类、不在前端重算偏差阈值。
   */
  label: RankingLabel;
};

export type RankingBoards = {
  category: RankingCategory;
  bubble: RankingItem[];
  underhyped: RankingItem[];
  fair: RankingItem[];
};
