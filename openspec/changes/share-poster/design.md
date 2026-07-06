## Context

`single-event-detail` 与 `bias-ranking` 已把单事件明细与三榜结果可视化展示出来；`web-app-shell-i18n` 提供了 `SnapshotTime` / `BiasLabel` / `EmptyState` / `ErrorState` 基元、i18n 插值 key 与三分类标签、`app`/`shared`/`pages` 分层与 `shared/api` `requestClient`；`image-proxy` 已定义后端同源图片代理端点（`GET /api/v1/image-proxy`，返回二进制图片流）用于规避 canvas 跨域污染。本 change 是 batch-2/wave-2 的**前端为主单端** change，负责把已展示结果转成可分享海报并按平台差异分发。

现状约束：前端 DOM 出图库尚未引入；浏览器分发能力（Web Share API、`navigator.clipboard.write` 图片、`canShare({files})`）在不同环境差异很大，必须按能力探测决定入口可见性与回退。偏差评分与三分类为纯规则计算、口径以 bias-algorithm §4/§5 为准，本 change 只消费已算好的展示数据，SHALL NOT 重算。

## Goals / Non-Goals

**Goals:**
- 在单事件明细与榜单两处提供受控离屏海报出图，复用两处已有展示数据源，不重算偏差。
- 出图口径严格对齐 PRD §4.5：`html-to-image` 主库、受控离屏子集、内联字体、DPR≥2、`document.fonts.ready`、海报内 Polymarket 图片经图片代理同源加载。
- 海报卡片区分展示「数据快照时间」与「海报生成时间」，文案随语言、市场内容不翻译。
- 分发按端与能力探测分派：移动端 Web Share 图片文件；桌面下载 / 复制链接 / 条件复制图片 / intent 分享 X·Telegram·Facebook·Reddit；各降级/失败态明确可重试。

**Non-Goals:**
- 不实现后端图片代理（`image-proxy` change 负责），本 change 只消费其端点。
- 不实现明细/排行页本体（各自 change），只在其上挂分享入口并读取其展示数据。
- 不做服务端分享页 / OG 富预览卡（PRD §4.5 明确本期不做）。
- 不做桌面横版海报（列为后续增强，MVP 桌面复用竖版）。
- 不做多库像素对齐兜底（PRD §4.5：出图失败直接降级下载/重试）。

## Decisions

- **D1 出图库选型（`html-to-image` 主库，无多库兜底）**：按 PRD §4.5 单库主选，出图失败直接降级为下载/重试。待入 `frontend/package.json`；封装在 `shared` 或分享模块内的 service，组件不直接调库细节。备选 `snapdom` / `dom-to-image` 不并存，避免体积与像素对齐复杂度。
- **D2 受控离屏渲染节点**：海报卡片为独立的受控 DOM 子树（off-screen，如绝对定位移出视口或隐藏挂载容器），只含受控元素、内联字体，规避背景图/滤镜/icon-font。出图前 `await document.fonts.ready`，以 `pixelRatio = max(devicePixelRatio, 2)` 调用 `html-to-image`。海报节点与页面主 DOM 解耦，保证明细/排行本体样式变化不影响出图。
- **D3 海报内 Polymarket 图片同源加载**：海报卡片中的 Polymarket 图片 `src` 一律改写为经后端图片代理的同源 URL（`GET /api/v1/image-proxy?url=<原图URL>`，契约见 `image-proxy`），出图前确保图片已 `decode`/加载完成，避免跨域污染 canvas。代理 URL 拼装走同源路径，不在组件里直连 Polymarket 图片域。
- **D4 时间双标注**：`data_snapshot_at` 来自展示数据源（`EventDetail` / `RankingBoards`）经 `SnapshotTime` 基元标注「数据快照时间」；「海报生成时间」取出图触发时刻的本地时间，二者独立字段独立标注，绝不复用同一值（对齐 PRD §5.3、`SnapshotTime` 基元预留的区分语义）。
- **D5 分发能力探测与分派**：runtime 探测 `navigator.share` + `navigator.canShare?.({files:[file]})`（移动端图片文件分享）、`navigator.clipboard.write` + `ClipboardItem`（复制图片，条件能力，需安全上下文）。矩阵：能分享文件 → 优先 Web Share；否则回退下载 + 复制链接；能复制图片 → 暴露「复制图片」，否则隐藏并以下载回退。intent 分享用各平台 share URL（X/Telegram/Facebook/Reddit）拼 `window.open`，文案经 i18n 插值、市场内容作变量。
- **D6 数据来源复用不重算**：单事件出图读 `single-event-detail` 的 `EventDetail`/`OptionAnalysis`（`price`/`heat`/`bias_score`/`label{zh,en}`）；榜单出图读 `bias-ranking` 的 `RankingBoards`/`RankingItem`（`event_slug`/`event_title`/`option_name`/`price`/`bias_score`/`label{zh,en}`）。「核心选项」对单事件取 `|bias|` 最大项（与列表卡片概览口径一致，PRD §4.1），前端只挑选不重算。
- **D7 分层与状态归属**：分享入口 + 出图/分发编排下沉为分享模块（`app`/`shared`/`pages` 既有分层内），route page 只承担 composition；出图/分发为一次性命令式动作（非服务端态），用本地组件态承载 loading/error，不引入 Query。失败态复用 `ErrorState`。
- **D8 i18n 文案**：新增分享相关 i18n key（en/zh）——分享入口、海报标题/来源/时间标签、intent 文案、各失败态；含市场内容句子一律插值 key，事件名/选项名作不翻译变量注入（PRD §4.6）。

## Risks / Trade-offs

- [受控离屏出图仍可能空白/字体缺失] → 内联字体 + `document.fonts.ready` + 受控子集规避易致空白元素；出图失败明确降级下载/重试而非静默（PRD §4.5）。
- [图片代理不可用导致海报缺图或出图失败] → 依赖 `image-proxy` 端点；代理失败时按出图失败路径降级重试，海报可在无远端图时仍出核心信息（占位/略过图片），不阻断分发。
- [Web Share / 复制图片能力跨浏览器差异大] → 全部 runtime 能力探测，不可用入口隐藏并保留下载 + 复制链接回退（PRD §4.5、AC-6）；用户取消分享不视为错误。
- [DPR≥2 在超大海报下内存/耗时偏高] → 竖版尺寸固定、受控子集限制节点规模；仅移动竖版，桌面复用竖版，横版后续再评估。
- [`html-to-image` 新依赖] → 单库、封装在 service 层，出图失败有降级路径，控制引入面。
