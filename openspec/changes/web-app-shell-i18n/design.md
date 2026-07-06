## Context

polyEdge 前端当前只有一个占位 `HomePage` 与最小 `app/`（`AppProviders` 仅挂 `QueryClientProvider`、`AppRouter` 单路由）、`shared/api`（`requestClient` + 错误归一）、`shared/styles/tokens.css`（含 hot/cold/fair 信号色语义）。`package.json` 已装 `i18next` / `react-i18next` / `i18next-browser-languagedetector` / `react-router-dom` v6 / `@tanstack/react-query` v5 / `zustand`。

本 change 是四个下游功能页（`event-list-and-input` / `single-event-detail` / `bias-ranking` / `share-poster`）的地基：确立路由/IA、i18n 架构、共享偏差展示基元、数据层装配与响应式外壳基座。所有取舍锚定 PRD §4.0 / §4.6 / §5.4 / §5.2 / §5.3 与 AC-8 / AC-9，标签口径锚定 bias-algorithm §4。硬约束：样式只用 `tokens.css` token；请求只经 `shared/api` 的 `requestClient`；复用既有 `app/` `shared/` `pages/` 分层。

## Goals / Non-Goals

**Goals:**

- 路由/IA：两顶层 Tab（事件列表 / 偏差排行，默认事件列表）+ 单事件明细面包屑/返回骨架 + 榜单回跳路由约定，功能页正文留占位 outlet（PRD §4.0）。
- i18n 架构：en/zh 两 resource、默认 en、切换入口、`localStorage` 持久化、含市场内容句子的占位符插值 key 约定、三分类标签中英文案（PRD §4.6 / §5.4、bias-algorithm §4）。
- 共享 UI 基元：偏差标签、选项指标行、快照时间标注、空态/错误态，纯展示、口径外部注入（PRD §4.3 / §5.2 / §5.3）。
- 数据层装配：`QueryClient` 默认项 + i18n Provider 接入 app providers；确立 `shared/api` service + `*.queries.ts` 消费模式（PRD §1.4 / §5.2 状态归属）。
- 响应式外壳基座：外壳级布局 token/断点约定，≤430px 无横向溢出（AC-9 基座）。

**Non-Goals:**

- 不实现各功能页业务（列表卡片、明细正文、三榜、海报出图）——归各自 change，本 change 只留 route 骨架与基元契约。
- 不做偏差计算：基元与页面消费「已算好的」偏差结果，算法在后端 `bias-scoring`（bias-algorithm）。
- 不做后端接口/迁移：前端单端。
- 不做市场内容机器翻译（PRD §1.3 / §4.6）。

## Decisions

### D1. 路由/IA：顶层 Tab 用嵌套路由 + URL 承载激活 Tab

在 `app/router/` 用 `createBrowserRouter` 建一个带 `AppShell` layout（顶层导航 + `<Outlet/>`）的路由树：`/`（重定向到事件列表）、`/events`（事件列表 Tab）、`/ranking`（偏差排行 Tab）、`/events/:eventId`（单事件明细，带面包屑/返回）。激活 Tab 由 URL path 决定而非组件内 state，保证刷新/直达/回跳稳定，且榜单项 `→ /events/:eventId` 回跳天然可达。功能页正文本 change 留占位组件，下游 change 替换。

- 备选：单页 + 组件内 `useState` 切 Tab。放弃：直达/刷新/回跳丢失当前视图，且明细回跳来源难以还原，不满足 PRD §4.0「面包屑/返回、榜单回跳」。

### D2. i18n：`i18next` + `react-i18next`，`shared/i18n/` 集中初始化

新增 `shared/i18n/`：`i18n.ts`（init：`fallbackLng: 'en'`、`supportedLngs: ['en','zh']`、插值默认关闭 HTML 转义按需）、`resources/en.json`、`resources/zh.json`、`locale.constants.ts`（语言枚举 + 存储 key）。语言检测/持久化用 `i18next-browser-languagedetector`，`order: ['localStorage','navigator']`、`caches: ['localStorage']`，但初始默认锁定为 `en`（PRD 要求默认 English，不因浏览器语言自动切中文——通过将 detector 的 `navigator` 作为次级且 `fallbackLng:'en'` 保证无偏好时落 en）。i18n Provider 在 `AppProviders` 内包裹。

- 插值 key 约定：含市场内容的句子统一形如 `"detail.topBias": "{{optionName}} has the highest bias in {{eventName}}"`，事件名/选项名作为 `t(key, { eventName, optionName })` 变量注入，禁止 `t('x') + optionName` 拼接（PRD §4.6）。约定写入 `shared/i18n/` 的说明性常量/注释与 resource 组织。
- 三分类标签 key：`bias.label.hot|cold|fair`，en/zh 两套值取自 bias-algorithm §4（Overheated · Bubble Risk / Underhyped · Value Opportunity / Fairly Priced 与中文）。

### D3. 共享偏差基元放 `shared/ui/`，纯展示、分类外部注入

偏差三分类是全产品共享语义（非某页私有），基元下沉 `shared/ui/`：`BiasLabel/`（入参 `category: 'hot'|'cold'|'fair'`，映射 `tokens.css` 的 `--color-{hot|cold|fair}-*` 与 `bias.label.*` 文案）、`OptionMetricsRow/`（赔率/热度/偏差评分/标签，数字经 i18n 本地化格式）、`SnapshotTime/`（快照时间标注，本地化时间格式）、`EmptyState/` 与 `ErrorState/`（标题/说明/操作插槽）。分类与数值一律由调用方注入，基元不含算法。tone/label/icon mapping 放 `*.constants.ts`、union type 放 `*.types.ts`（遵循 file-organization）。

- 备选：把基元放各功能页私有。放弃：四页重复、标签口径/配色易漂移，违背「共享偏差展示基元」目标。

### D4. 数据流：`shared/api` service + 模块内 `*.queries.ts`，服务端态经 Query、语言经本地态

沿用既有 `request`/`requestClient`。约定下游功能页在自己模块内写 `*.api.ts`（调 `request`）+ `*.queries.ts`（`useQuery` 封装），本 change 在 `AppProviders` 配置 `QueryClient` 默认项（`staleTime`/`retry`/`refetchOnWindowFocus` 合理默认，服务端快照类数据）。偏差结果/降级标注/快照时间属服务端态经 Query 承载；语言偏好属本地态，经 `i18next-browser-languagedetector` 的 `localStorage` 承载（PRD §5.2 状态归属）。语言若需跨组件读取，用轻量 zustand store 或直接 `useTranslation().i18n.language`，优先后者不引入多余 store。

### D5. 响应式基座：外壳级布局 token + 单一移动断点

外壳布局用 flex/grid + `min-width:0` + `overflow-wrap`/`text-overflow` 处理超长英文事件名/选项名（AC-9）。断点采用移动优先单断点（≤430px 为窄屏基线），断点值与外壳级间距若 `tokens.css` 缺失则在其中新增布局 token（不改既有语义色）。功能页各自窄屏布局（如排行三榜分段 Tab）归各自 change，本 change 只保证外壳与基元不溢出。

## Risks / Trade-offs

- [detector 可能因浏览器语言把默认带偏成中文，违反「默认 English」AC-8] → detector `order` 以 `localStorage` 优先、`fallbackLng:'en'`，并在无存储偏好时锁定 en 初值；加一条针对「无偏好 navigator=zh」的用例验证默认仍为 en。
- [路由骨架与下游功能页 change 的 outlet/路径契约不一致导致返工] → 在 design 固化路径（`/events`、`/ranking`、`/events/:eventId`）与占位 outlet 命名，作为下游预留契约明确交付。
- [基元 props 设计不当，下游被迫改基元] → 基元只收「已算好的展示数据 + 分类枚举」，不耦合数据获取；tone/label mapping 收敛到 `*.constants.ts`，扩展新展示位不动核心 props。
- [tokens.css 新增布局 token 触碰既有语义色] → 仅新增布局/断点类 token，语义色 token 只读不改，改动范围限外壳布局。
- [过度装配数据层却无真实接口] → 本 change 只配 `QueryClient` 默认项与消费约定，不 mock 业务接口，避免与后端契约提前耦合。

## Migration Plan

- 纯新增/装配，无破坏性变更、无迁移：扩展 `app/router`、`app/providers`，新增 `shared/i18n/`、`shared/ui/` 基元，按需补 `tokens.css` 布局 token；`HomePage` 由 `AppShell` + 事件列表占位替代（占位不含业务）。
- 回滚：移除新增路由/Provider/基元即回到占位首页，无数据副作用。

## Open Questions

- 无 per-option 参与数据等降级标注文案的最终 i18n 措辞，以功能页 change 落地时对齐 bias-algorithm §3.5；本 change 只提供空态/错误态与标注基元容器，不锁死具体降级文案。
