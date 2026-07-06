/**
 * 分享海报模块类型（share-poster，PRD §4.5、design D6/D7）。
 *
 * 本模块只消费上游已算好的展示数据（`single-event-detail`、`bias-ranking`），
 * 不重算偏差、不反推分类。海报信号有两种呈现：
 *   - `category`：来自 `bias-ranking` 榜别分组（合法三分类，驱动 `BiasLabel`）。
 *   - `text`：来自 `single-event-detail` 的已本地化 `label{zh,en}` 文案（契约无 category
 *     枚举，沿用既有中性文案兜底，前端不重算阈值分类）。
 */

import type { IsoDateTimeString } from '../../../services/types';
import type { BiasCategory } from '../../../shared/ui/BiasLabel';

/** 海报偏差信号：榜别三分类 / 中性文案兜底 / 无（不适用或被排除）。 */
export type PosterSignal =
  | { kind: 'category'; category: BiasCategory }
  | { kind: 'text'; text: string }
  | { kind: 'none' };

/** 海报卡片内容（由各页面用其展示数据组装，市场内容不翻译）。 */
export type SharePosterContent = {
  /** 眉标 i18n key（如榜单名或通用「偏差结果」）。 */
  eyebrowKey: string;
  /** 主标题：事件标题（市场内容，英文源文本不翻译）。 */
  headline: string;
  /** 核心选项名（市场内容，不翻译）。 */
  coreOptionName: string;
  /** 核心选项隐含概率，0..1 区间（由上游展示数据注入，海报不重算）。 */
  impliedProbability: number;
  /** 偏差评分，上游算好，前端不重算。 */
  biasScore: number;
  /** 偏差信号呈现方式。 */
  signal: PosterSignal;
  /**
   * 数据快照时间（`data_snapshot_at`）；仅当展示数据源提供时存在。
   * 单事件明细提供；榜单聚合契约暂无该字段则缺省（见交付风险）。
   */
  dataSnapshotAt?: IsoDateTimeString;
  /** 可选 Polymarket 图片原始 URL；渲染时经图片代理同源加载。 */
  imageUrl?: string;
};

/** 出图结果：图片 Blob + 下载文件名。 */
export type PosterImage = {
  blob: Blob;
  fileName: string;
};

/** 后端上传后的海报图片地址。 */
export type UploadedPosterImage = {
  url: string;
  path: string;
  contentType: string;
  size: number;
};

/** 运行时分发能力探测结果（design D5）。 */
export type ShareCapabilities = {
  /** 支持 Web Share 且可分享文件（移动端优先）。 */
  canWebShareFiles: boolean;
  /** 支持复制图片到剪贴板（条件能力，需安全上下文）。 */
  canCopyImage: boolean;
  /** 支持复制链接文本。 */
  canCopyLink: boolean;
};
