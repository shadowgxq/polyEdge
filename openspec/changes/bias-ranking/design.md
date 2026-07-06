## Context

`web-app-shell-i18n` 已建立外壳：`createBrowserRouter` 下 `/ranking` 是「偏差排行」顶层 Tab（当前为占位 outlet，归本 change 填充），`/events/:eventId` 是单事件明细（回跳目标），并下沉了共享偏差基元 `shared/ui/`（`BiasLabel` 入参 `category: 'hot'|'cold'|'fair'` 映射 `tokens.css` 信号色 + `bias.label.*` 文案；`EmptyState`/`ErrorState` 收标题/说明 + 操作插槽；`SnapshotTime`/`OptionMetricsRow`）。数据层约定：模块内 `*.api.ts`（经 `shared/api` `requestClient`）+ `*.queries.ts`（`useQuery`）承载服务端态，语言经 `i18next`。

`analysis-api` 已定义排行接口：`GET /api/v1/rankings`，query `category`（`hot`|`world_cup`，默认 `hot`）+ `top_n`（默认取配置），返回 `ApiResponse<RankingBoards>`，`RankingBoards = { category, bubble: RankingItem[], underhyped: RankingItem[], fair: RankingItem[] }`，`RankingItem = { event_slug, event_title, option_name, price, bias_score, label: { zh, en } }`；三榜互斥无交集、泡沫降序 / 冷门升序、TopN 截取与空榜 `[]` 均由后端保证。

约束（项目硬约束）：样式只用 `tokens.css` token；请求只经 `requestClient`；服务端态经 Query；route page 只做 composition / 状态归属 / 编排，UI 区块下沉命名组件；复用既有 `app/` `shared/` `pages/` 分层，不新造平行结构。

## Goals / Non-Goals

**Goals:**

- 填充 `/ranking` outlet：按当前分类展示泡沫/冷门/合理三榜，每项含事件归属、选项、赔率、偏差评分、偏差标签，可回跳单事件明细（PRD §4.4、AC-4）。
- 各榜独立空态、页面级加载/错误态（可重试），降级不空白不整页报错（PRD §5.2、AC-5）。
- 窄屏卡片纵向 + 三榜分段 Tab，超长事件名/选项名截断/换行，无横向溢出（AC-9）；只读无交易入口（AC-7）。
- 沿用 `*.api.ts` + `*.queries.ts` 数据模式、`shared/ui` 基元、i18n 插值 key 约定。

**Non-Goals:**

- 不做聚合计算与分档/排序/TopN 截取——三榜口径、互斥无交集、排序方向、TopN 全由后端 `analysis-api` + `bias-algorithm §5` 决定，前端只按返回顺序展示。
- 不改外壳路由/基元/i18n 地基，不实现列表页（`event-list-and-input`）、明细页（`single-event-detail`）、海报（`share-poster`）、后端接口。
- 不做分类切换器本体归属之争：分类（`hot`/`world_cup`）来源沿用外壳既定 Tab/分类态；本页读取「当前分类」作为请求参数（见 D4）。

## Decisions

### D1. route page 只做 composition，三榜与榜单项下沉命名组件

`pages/ranking/RankingPage.tsx` 只承担：读取当前 `category`、发起排行 Query、按状态（loading / error / success）编排。三榜展示下沉为组件：`RankingBoards`（三榜容器，负责宽屏并列 / 窄屏分段 Tab 布局）、`RankingBoard`（单榜：标题 + 榜单项列表 + 该榜空态）、`RankingItemRow`（单条榜单项：事件标题、选项名、赔率、偏差评分、`BiasLabel`，整行为回跳入口）。组件放 `pages/ranking/components/`，纯展示、数据由 page 注入，遵循 component-splitting / file-organization。

- 备选：全部塞进 page。放弃：违反 route page 只做 composition 的项目约束，且三榜/榜单项复用与窄屏布局难维护。

### D2. 三榜 → 分类枚举映射，偏差标签复用 `BiasLabel` 基元

后端 `RankingItem.label` 是 `{ zh, en }` 文案对象，而共享 `BiasLabel` 基元入参是 `category: 'hot'|'cold'|'fair'`（映射信号色 + `bias.label.*` i18n 文案）。榜单项所属榜别与三分类一一对应：`bubble → hot`（泡沫风险）、`underhyped → cold`（冷门机会）、`fair → fair`（合理）。因此前端由「该项所在的榜」推导 `category` 传给 `BiasLabel`，视觉与文案统一走基元 + `tokens.css` 信号色，不直接渲染后端 `label.zh/en` 字符串（避免与基元文案口径漂移）。后端 `label` 字段保留在类型中备用但不作为渲染唯一来源。

- 备选：直接渲染 `label.zh/en`。放弃：绕过共享基元会导致标签配色/文案在四页间漂移，违背基元「统一偏差展示口径」目标。

### D3. 服务端态经 Query，分类为 queryKey 维度

新增 `pages/ranking/ranking.api.ts`：`fetchRankings(params: { category, topN? })` 经 `requestClient` 调 `GET /api/v1/rankings`，解包 `ApiResponse.data`。`ranking.queries.ts`：`useRankingsQuery(category)` 以 `['rankings', category]` 为 queryKey，`top_n` 用后端默认（不传，避免前端硬编码 N），沿用外壳 `QueryClient` 默认项。偏差结果属服务端快照态，仅经 Query 承载；组件内不直接发请求。类型 `RankingBoards` / `RankingItem` / `RankingCategory` 放 `ranking.types.ts`，字段名对齐后端 snake_case 契约。

### D4. 分类来源：读「当前 Tab 分类」，本页不新造分类切换器

排行聚合基数是「当前 Tab 默认列表分类」（`hot`/`world_cup`），该分类语义属外壳/列表既有态。本 change 从既有分类来源读取当前分类作为请求参数（若外壳/列表已把分类落在 URL query 或共享态则复用之；缺失时以 `hot` 为默认并预留 `category` prop 注入点），不在排行页私造与列表不一致的第二套分类切换 UI。分类切换器归属若由 `event-list-and-input` 或外壳提供，则本页只消费其值。

- 备选：排行页自带独立分类下拉。放弃：与列表分类语义割裂、易不一致；PRD §4.4 明确聚合基数是「当前 Tab 默认列表」。

### D5. 三榜布局：宽屏并列 / 窄屏分段 Tab（AC-9）

`RankingBoards` 用 `tokens.css` 断点：≥断点宽屏三榜横向分区（各列纵向滚动，`min-width:0` + `overflow-wrap` 防溢出）；≤430px 窄屏改为三榜分段 Tab（bubble/underhyped/fair 三段切换，单榜卡片纵向排列），避免三列横向溢出。分段 Tab 的激活段为组件内本地 UI 态（非路由态，属纯展示交互）。榜单项行内事件名/选项名超长时截断/换行。布局若需断点/间距 token 而 `tokens.css` 缺失，仅新增布局 token，不改语义色。

### D6. 各榜独立空态、页面级加载/错误态

- 页面级：Query `isPending` → 加载态（骨架/占位）；`isError` → `ErrorState` + 重试（`refetch`），不整页崩。
- 榜级：success 后某榜数组为 `[]` → 该榜位渲染 `EmptyState`（本地化说明，如「暂无泡沫风险选项」），其余两榜正常渲染（PRD §5.2、AC-5）。空态与错误态文案经 i18n，含事件/选项内容的句子用插值 key（如 `t('ranking.item.aria', { eventTitle, optionName })`），不字符串拼接。

### D7. 回跳复用外壳契约，只读无交易入口

`RankingItemRow` 整行为可点击回跳，用外壳 `/events/:eventId` 契约（`event_slug` 作为 `:eventId`，经 react-router `Link`/`navigate`）。全页只读展示，无任何交易/下单/钱包入口（AC-7）。回跳交互提供键盘可达与 `aria-label`（含事件名/选项名，经 i18n 插值）。

## Risks / Trade-offs

- [后端 `RankingItem.label` 文案与前端 `BiasLabel` 基元文案两套口径漂移] → D2 以「榜别→category→基元」为唯一渲染源，后端 `label` 仅备用；标签口径单一来源在基元，锚定 bias-algorithm §4。
- [`event_slug` 作为回跳 `:eventId` 与明细页 slug 契约不一致] → 沿用 `analysis-api` 契约中 `event_slug` 与 `GET /api/v1/events/{slug}` 同一 slug 语义、外壳 `/events/:eventId` 回跳约定；集成期若明细页参数名不同仅在回跳处对齐，不改数据契约。
- [分类来源在外壳/列表尚未最终固化，排行读不到当前分类] → D4 预留 `category` 注入点 + `hot` 默认兜底，分类切换器归属由外壳/列表 change 决定，本页只消费不新造，避免返工。
- [窄屏三榜分段 Tab 与宽屏并列两套布局分叉增加复杂度] → 单一 `RankingBoard` 组件复用，仅容器 `RankingBoards` 按断点切布局；分段激活为本地 UI 态，不引入路由/store。
- [空榜与错误态混淆导致误报] → 严格区分：`isError`（拉取失败）走页面 `ErrorState` 可重试；success 下 `[]` 走榜级 `EmptyState`，二者文案与入口不同（PRD §5.2）。

## Migration Plan

- 纯新增：`pages/ranking/`（`RankingPage.tsx` + `components/` + `ranking.api.ts` / `ranking.queries.ts` / `ranking.types.ts`），挂到外壳 `/ranking` 占位 outlet（替换占位组件）。无破坏性变更、无数据迁移。
- 依赖顺序：`web-app-shell-i18n`（路由/基元/i18n/QueryClient）与 `analysis-api`（`GET /api/v1/rankings`）先落地；本 change 集成对接其契约。
- 回滚：恢复 `/ranking` 占位 outlet、移除 `pages/ranking/` 即可，无副作用。

## Open Questions

- 「当前分类」的最终承载（URL query / 外壳共享态 / 列表 change 提供的切换器）由外壳/`event-list-and-input` 固化；本 change 按 D4 预留注入点，不阻塞。
- 排行页是否需展示各榜数据快照时间（`SnapshotTime`）：当前 `RankingBoards` 契约未含 `data_snapshot_at`，如后端后续补充再接入基元；本 change 不臆造该字段。
