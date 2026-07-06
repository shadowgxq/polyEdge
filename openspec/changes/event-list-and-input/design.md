## Context

web-app-shell-i18n 已提供：`AppShell` layout + `/events` 路由 outlet（占位组件待替换）、共享基元 `BiasLabel`（`category:'hot'|'cold'|'fair'`）/ `OptionMetricsRow` / `SnapshotTime` / `EmptyState` / `ErrorState`、i18n（en/zh，含 `{{eventName}}`/`{{optionName}}` 插值 key 约定、`bias.label.*` 三分类文案）、app providers 层的 `QueryClient`、`shared/api` 的 `requestClient`。analysis-api 已冻结三个接口契约（见 Decisions）。本 change 是前端单端，只填充 `/events` 页面正文与事件输入交互，消费上述地基与接口，不实现后端、不做单事件明细正文（single-event-detail）、不做排行页（bias-ranking）。硬约束：样式只用 `tokens.css` token；请求经 `shared/api` service（不在组件直接发请求）；服务端态经 TanStack Query；复用 `app/shared/pages` 分层，route page 只做路由参数/页面级 composition/状态归属/数据流编排，独立 UI 区块下沉命名组件。

## Goals / Non-Goals

**Goals:**

- `/events` 列表页正文：热门/世界杯分类 Tab、事件卡片（事件名 + 选项赔率概览 + 概览偏差标签 + 快照时间 + 不适用标注）、规模上限与加载更多（PRD §4.1、AC-1）。
- 事件输入：手动链接（前端 URL 形态校验 → `resolve`）、名称搜索（`search` 候选选择 + `local_cache` 回退标注），列表/世界杯/手动三路均定位到 `/events/:eventId`（PRD §4.2、AC-2）。
- 各降级空态/错误态复用共享基元，不静默失败（PRD §5.2、AC-5）。
- 只读无交易入口（AC-7）、≤430px 窄屏无溢出（AC-9）。

**Non-Goals:**

- 不实现后端接口/slug 提取/搜索/本地模糊（属 analysis-api）。
- 不实现单事件明细正文（single-event-detail）、排行页（bias-ranking）、外壳/i18n/基元地基本身（web-app-shell-i18n）。
- 不自算偏差/分类阈值：卡片概览标签口径由后端返回，前端仅展示（bias-algorithm §4/§6）。
- 不做市场内容机器翻译（事件名/选项名原文透传）。

## Decisions

### D1. 页面结构落 `pages/events/`，route page 只做编排

新增 `pages/events/EventsPage.tsx` 替换 web-app-shell-i18n 在 `/events` 的占位。route page 只承担：分类 Tab 状态归属、分页/加载更多状态、输入弹层/区块开合、数据流编排与导航。独立 UI 区块下沉为同模块命名组件：`EventCategoryTabs`（热门/世界杯分段 Tab）、`EventCard`（单卡片）、`EventCardList`（列表 + 加载更多）、`EventInputPanel`（链接/名称输入）、`EventSearchResults`（候选列表 + 回退标注）。遵循 file-organization：目录 + `index.ts` 出口，类型放 `events.types.ts`，接口调用放 `events.api.ts`，Query 封装放 `events.queries.ts`。

- 备选：把卡片/输入都塞进 `EventsPage`。放弃：route page 承担 UI 细节，违背「route page 只做 composition」与组件拆分规范。

### D2. 数据层：`events.api.ts`（`request`）+ `events.queries.ts`（Query），服务端态经 Query

沿用 web-app-shell-i18n 确立的模式。`events.api.ts` 用 `shared/api` 的 `request` 封装三个调用：`fetchEvents({ category, page, page_size })`、`resolveEvent({ input })`、`searchEvents({ q, limit })`。`events.queries.ts`：

- 列表用 `useInfiniteQuery`（`queryKey: ['events', category]`，`getNextPageParam` 依 `has_more` 取 `page+1`），天然支持「加载更多」与分类切换缓存隔离。
- 名称搜索用受控 `useQuery`（`enabled` 依提交动作，`queryKey: ['events','search', q]`）。
- 链接解析用 `useMutation`（`resolve` 为一次性提交动作，成功后 `navigate`）。

`QueryClient` 默认项由地基提供；组件内不出现 axios/fetch 直接调用。

### D3. 契约复用（不自拟，锚定 analysis-api tasks §6）

- `GET /api/v1/events`｜query `category`(`hot|world_cup`,默认`hot`)/`page`(默认1)/`page_size`(默认配置上限)｜`data`=`{ category, items: EventCard[], has_more }`；`EventCard`=`{ slug, title, options:[{name, price}], overview_label:{zh,en}|null, overview_option_name|null, applicable, data_snapshot_at }`。
- `POST /api/v1/events/resolve`｜body `{ input }`｜`data`=`EventDetail`（明细结构归 single-event-detail 消费；本 change 只用其 `slug` 做导航）；解析不出为非 `code=0` 错误态。
- `GET /api/v1/events/search`｜query `q`/`limit`｜`data`=`{ candidates:[{slug,title}], search_scope:'upstream'|'local_cache' }`。

前端 TS 类型在 `events.types.ts` 按上述契约定义，`ApiResponse[T]` 解包复用 `shared/api` 既有归一。概览偏差标签的三分类映射直接用后端 `overview_label`（已含 zh/en）传给 `BiasLabel`；`applicable=false`（`overview_label=null`）走「不适用」分支。

### D4. 事件输入：前端只做 URL 形态校验，slug 提取交后端

`EventInputPanel` 对链接输入做纯前端形态校验（正则判定是否 Polymarket 事件链接/slug 形态，如 `polymarket.com/event/<slug>` 或裸 slug），形态非法就地提示不发请求；形态合法调 `resolve`（mutation）。名称输入调 `search`。二者以简单判别（含 `polymarket.com`/URL 形态 → 链接路径；否则 → 名称搜索路径）或分栏输入区分，实现阶段取更简路径。`search_scope==='local_cache'` 时在候选区上方渲染 i18n 标注「仅在当前收录事件范围内搜索」。

- 备选：前端自己提取 slug 拼明细路由。放弃：PRD §4.2 明确 slug 提取/有效性判定归后端，前端仅形态校验。

### D5. 降级/空态/错误态映射（复用基元）

- 世界杯 `items=[]` → `EmptyState`（「当前无世界杯相关事件」+ 切回热门 Tab 操作）。
- 列表请求 `isError` → `ErrorState`（重试 = `refetch`）。
- `resolve` 未找到 / `search` 空候选 → `EmptyState`（重试引导）。
- 卡片 `applicable=false` → 卡内标注「不适用偏差分析」，不渲染 `BiasLabel`。
- 加载/追加中 → 骨架/加载态，不空白。

文案统一走 i18n（含市场内容用插值 key，不字符串拼接）。

### D6. 只读与窄屏（AC-7 / AC-9）

页面无任何交易/钱包入口。卡片/Tab/输入用 flex/grid + `min-width:0` + `overflow-wrap`/`text-overflow` 处理超长英文名，样式只用 `tokens.css` token（含地基新增的布局/断点 token）；分类 Tab 窄屏用分段控件避免横向溢出。

## Risks / Trade-offs

- [analysis-api 接口字段名/结构在并行开发中微调] → 类型集中 `events.types.ts`，仅此处对齐 tasks §6 冻结契约；集成期只改类型映射不散落组件。
- [`resolve` 返回 `EventDetail` 全量但本 change 只需 `slug`] → 只依赖 `slug` 字段做导航，明细正文渲染归 single-event-detail，避免与其契约耦合。
- [链接 vs 名称的输入判别不准导致误走接口] → D4 用明确形态校验 + 兜底（形态非法即提示），必要时改分栏输入消歧。
- [`useInfiniteQuery` 分类切换缓存串扰] → `queryKey` 带 `category` 隔离，切 Tab 各自缓存。
- [基元 props 不满足卡片「不适用」标注/选项赔率概览布局] → 优先用基元既有 props 组合（`BiasLabel` + 文本标注），确有缺口反馈 web-app-shell-i18n，不在本 change 改基元核心。

## Migration Plan

- 纯新增：新增 `pages/events/` 模块，替换 `/events` 占位组件的引用；无破坏性变更、无后端/DB/迁移。
- 回滚：还原 `/events` 路由指向占位组件、移除 `pages/events/` 即可，无数据副作用。
- 集成顺序：依赖 web-app-shell-i18n（路由/基元/i18n/Query）与 analysis-api（三接口）先落地；接口未就绪时可先按 `events.types.ts` 契约开发并以 Query 空态占位。

## Open Questions

- 链接输入与名称输入是合并单输入框（前端判别）还是分栏，取实现阶段更简清晰者；不影响对外契约。
- 每页 `page_size` 具体默认值取后端配置上限（建议 20），前端不写死，随接口默认。
