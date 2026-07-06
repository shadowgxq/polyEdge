## Why

用户在单事件明细看清偏差、或在排行发现全局机会后，需要一键把结果做成**可分享的偏差结果卡片**并分发到社媒，以支持传播（PRD §1.2「支持传播」、§4.5、AC-6）。当前 `single-event-detail` 与 `bias-ranking` 已把可视结果展示出来，`web-app-shell-i18n` 提供了 UI 基元（含 `SnapshotTime` 预留「数据快照时间 vs 海报生成时间」区分）、`EmptyState`/`ErrorState` 与 i18n 插值约定，`image-proxy` 已定义海报内 Polymarket 图片同源加载契约——但把结果转成图片、并按平台差异分发/降级的能力尚未落地。

## What Changes

- 在单事件明细与某个榜单两处提供分享入口，触发受控离屏（off-screen）海报出图（PRD §4.5、AC-6）。
- 前端 DOM 转图片，**主选单库 `html-to-image`**（待入 `frontend/package.json`）：受控离屏子集渲染、内联字体、按 `devicePixelRatio`（≥2）高清渲染、出图前等待 `document.fonts.ready`；海报内 Polymarket 图片经**后端图片代理**（`image-proxy`）同源加载以规避 canvas 跨域污染（PRD §4.5、§1.4）。出图失败直接降级为下载/重试，不追求多库像素对齐兜底。
- 海报卡片内容：事件/榜单标题、核心选项与偏差标签、偏差评分、**区分展示的数据快照时间（`SnapshotTime`）与海报生成时间**、来源标注（Polymarket）；文案跟随当前界面语言，市场内容（事件名/选项名）不翻译（PRD §4.5、AC-6、§4.6）。
- 分发通道：移动端经 Web Share API 分享**图片文件**到系统原生面板；桌面端提供下载图片、复制链接、intent 分享到 X / Telegram / Facebook / Reddit；**复制图片到剪贴板为条件能力**——支持的浏览器（安全上下文）可用，否则该入口自动隐藏并回退下载（PRD §4.5、AC-6）。
- 降级与失败态：不支持 Web Share / 不支持分享文件时退化为下载 + 复制链接；出图或分享失败均呈现明确错误态并可重试（复用 `ErrorState`），不静默失败（PRD §5.2、AC-5、AC-6）。
- MVP 仅提供移动端竖版海报尺寸（移动优先），桌面复用竖版；桌面横版列为后续增强。本期不生成服务端分享页 / OG 富预览卡。

## Capabilities

### New Capabilities
- `share-poster`: 分享海报与分发能力——单事件结果 / 榜单两处分享入口、受控离屏海报出图（`html-to-image`、内联字体、DPR≥2、`document.fonts.ready`、经图片代理同源加载 Polymarket 图片）、海报卡片内容（标题 / 核心选项 + 偏差标签 / 偏差评分 / 区分展示数据快照时间与海报生成时间 / 来源标注，文案随语言）、分发通道（移动端 Web Share 图片文件；桌面端下载 / 复制链接 / 条件复制图片 / intent 分享 X·Telegram·Facebook·Reddit）与各降级/失败态。

### Modified Capabilities
<!-- 无：不改动 single-event-detail / bias-ranking / web-app-shell-i18n / image-proxy 已定义的 requirement，仅复用其展示数据来源、UI 基元与同源加载契约。 -->

## Impact

- 前端为主单端：`frontend/src/` 下新增分享模块（分享入口触发 + 受控离屏海报卡片组件 + 出图/分发 service + 私有子组件），在单事件明细与排行两处挂入分享入口。
- 新增依赖：`html-to-image`（待列入 `frontend/package.json`）。
- 复用依赖：`single-event-detail`（单事件展示数据来源 `EventDetail`/`OptionAnalysis`，不重算偏差）、`bias-ranking`（榜单展示数据来源 `RankingBoards`/`RankingItem`）、`web-app-shell-i18n`（`SnapshotTime`/`BiasLabel`/`EmptyState`/`ErrorState` 基元、i18n 插值 key 与三分类标签、`app`/`shared`/`pages` 分层）、`image-proxy`（海报内 Polymarket 图片经后端同源图片代理 `GET /api/v1/image-proxy` 加载）。
- 依赖后端接口：图片代理（`image-proxy`），本 change 只消费不实现。
- 不涉及：后端图片代理实现、明细/排行页本体、服务端分享页 / OG 富预览。
- 硬约束：样式只用 `tokens.css` token；网络请求经 `shared/api` 的 `requestClient`（图片代理 URL 走同源路径）；复用既有分层与 `web-app-shell-i18n` 基元，不另起平行结构。
