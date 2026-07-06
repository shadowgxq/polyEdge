## Why

PRD §4.4 要求对当前 Tab 默认事件列表做跨事件聚合，输出「高热度·泡沫风险榜 / 低热度·冷门机会榜 / 合理选项列表」三榜，帮用户一屏发现全局偏差机会并回跳单事件核对（AC-4）。外壳（`web-app-shell-i18n`）已预留 `/ranking` 顶层 Tab 与占位 outlet、回跳契约与共享偏差基元，后端（`analysis-api`）已定义 `GET /api/v1/rankings` 三榜契约，现需前端填充该 Tab 正文，把三榜真正展示出来。

## What Changes

- 填充 `/ranking` 顶层 Tab 正文：消费 `GET /api/v1/rankings`，按当前分类（`hot` / `world_cup`）展示泡沫风险榜、冷门机会榜、合理列表三榜。
- 每榜按后端已截取的 TopN 顺序渲染榜单项（泡沫降序 / 冷门升序 / 合理），每项展示所属事件（标题）、选项名、赔率、偏差评分与三分类偏差标签（复用 `shared/ui` 基元）。
- 榜单项可点击回跳 `/events/:eventId`（复用外壳回跳契约），把偏差机会带回单事件明细核对。
- 各榜独立空态：某榜为空数组时该榜展示空态、其余两榜正常渲染，不整页报错（PRD §5.2、AC-5）。
- 加载态 / 拉取失败错误态（可重试），复用 `shared/ui` 的 `EmptyState` / `ErrorState`；只读展示，无任何交易入口（AC-7）。
- 窄屏（≤430px）采用卡片纵向排列 + 三榜分段 Tab 切换，避免横向溢出；宽屏三榜并列/分区（AC-9）。
- 新增排行模块的 `*.api.ts`（经 `requestClient`）+ `*.queries.ts`（`useQuery`），route page 只做 composition 与状态归属编排。

## Capabilities

### New Capabilities
- `bias-ranking-view`: 偏差排行页正文——按当前分类展示泡沫/冷门/合理三榜、每项事件归属与回跳、各榜独立空态、加载/错误态、窄屏卡片纵向 + 三榜分段 Tab 的只读排行视图。

### Modified Capabilities
<!-- 无：本 change 只填充 web-app-shell-i18n 预留的 /ranking outlet，消费其路由/回跳/基元与 analysis-api 排行接口，不修改其 spec 级行为。 -->

## Impact

- 前端新增排行页模块（route page + 榜单区块组件 + `*.api.ts` / `*.queries.ts`），挂到外壳 `/ranking` 路由的占位 outlet。
- 消费外壳（`web-app-shell-i18n`）：`/ranking` 路由、`/events/:eventId` 回跳契约、`BiasLabel` / `OptionMetricsRow`(可选) / `EmptyState` / `ErrorState` 基元、i18n 插值 key 约定、`QueryClient` 装配与 `shared/api` `requestClient`。
- 消费后端（`analysis-api`）：`GET /api/v1/rankings`（`category` + `top_n` → `RankingBoards`）。
- 依赖 `web-app-shell-i18n`、`analysis-api` 先落地；不改后端、不做聚合计算（后端算，前端只展示）、不碰列表/明细/海报页。
