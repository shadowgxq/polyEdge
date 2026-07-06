<!-- 本 change 为前端单端（frontend/），全部任务属 ## 前端 范围；无后端分节。 -->

## 1. 前端 · i18n 基建（PRD §4.6 / §5.4、AC-8、bias-algorithm §4）

- [x] 1.1 新增 `frontend/src/shared/i18n/`：`i18n.ts` 初始化 `i18next` + `react-i18next`（`fallbackLng:'en'`、`supportedLngs:['en','zh']`），接入 `i18next-browser-languagedetector`（`order:['localStorage','navigator']`、`caches:['localStorage']`），保证无既存偏好时默认落 English。
- [x] 1.2 新增 `shared/i18n/locale.constants.ts`：语言枚举（`en`/`zh`）与 `localStorage` 存储 key；`index.ts` 暴露初始化实例与常量。
- [x] 1.3 新增 `shared/i18n/resources/en.json`、`resources/zh.json`：导航/按钮/空态/错误提示等基础 UI 文案，并落地含市场内容的插值 key 约定（形如 `{{eventName}}`/`{{optionName}}`，变量注入不拼接）。
- [x] 1.4 在 resource 内定义偏差三分类标签 key `bias.label.hot|cold|fair`，en/zh 两套文案取自 bias-algorithm §4（Overheated · Bubble Risk / Underhyped · Value Opportunity / Fairly Priced 与对应中文）。
- [x] 1.5 实现语言切换入口组件（`shared/ui/LanguageSwitcher/`），切换即时生效并经 detector 持久化到 `localStorage`；补测：切换生效、刷新保持、无偏好默认 en。

## 2. 前端 · 应用装配与数据层基座（PRD §1.4 / §5.2）

- [x] 2.1 在 `app/providers/AppProviders.tsx` 接入 i18n Provider（包裹或引入 `shared/i18n` 初始化），与既有 `QueryClientProvider` 组合。
- [x] 2.2 配置 `QueryClient` 默认项（`staleTime` / `retry` / `refetchOnWindowFocus` 面向服务端快照类数据的合理默认），承载偏差结果/降级标注/快照时间等服务端状态。
- [x] 2.3 复核 `shared/api`：确认下游经 `request`/`requestClient` 调用的 service + `*.queries.ts` 消费约定可用（本 change 不新增业务接口，仅确立模式与默认配置）。

## 3. 前端 · 路由与应用外壳（PRD §4.0、AC-9 基座）

- [x] 3.1 在 `app/router/AppRouter.tsx` 重构为带 `AppShell` layout 的嵌套路由：`/` 重定向到事件列表、`/events`（事件列表 Tab）、`/ranking`（偏差排行 Tab）、`/events/:eventId`（单事件明细）。
- [x] 3.2 实现 `AppShell`（`app/router/` 或 `widgets/app-shell/`）：顶层两 Tab 导航（事件列表 / 偏差排行）+ `<Outlet/>`，激活 Tab 由 URL path 决定；默认进入事件列表。
- [x] 3.3 为 `/events`、`/ranking`、`/events/:eventId` 提供占位页组件（含单事件明细的面包屑/返回入口与「榜单项 → /events/:eventId」回跳约定），功能页正文留给下游 change 填充。
- [x] 3.4 用 `AppShell` + 事件列表占位替代现有占位 `HomePage`（占位不含业务）；补测：默认落事件列表、两 Tab 切换、明细面包屑返回、榜单回跳路由可达。

## 4. 前端 · 共享偏差展示基元与状态组件（PRD §4.3 / §4.4 / §5.2 / §5.3）

- [x] 4.1 `shared/ui/BiasLabel/`：入参 `category:'hot'|'cold'|'fair'`，映射 `tokens.css` 的 `--color-{hot|cold|fair}-*` 与 `bias.label.*` i18n 文案；tone/label mapping 放 `BiasLabel.constants.ts`、union type 放 `*.types.ts`；纯展示、不含算法。
- [x] 4.2 `shared/ui/OptionMetricsRow/`：呈现赔率（隐含概率）/热度/偏差评分/偏差标签，数字随语言本地化格式、评分数值口径不变；数据由外部注入。
- [x] 4.3 `shared/ui/SnapshotTime/`：数据快照时间标注（本地化时间格式），预留与「海报生成时间」区分展示的语义（海报生成时间由 share change 提供）。
- [x] 4.4 `shared/ui/EmptyState/` 与 `shared/ui/ErrorState/`：标题/说明 + 可选操作（重试/切 Tab）插槽，文案经 i18n，支撑 PRD §5.2 各降级态；不空白、不整页报错。
- [x] 4.5 为各基元补最小单测（分类→视觉/文案映射、i18n 文案切换、空/错态操作回调），并按 file-organization 用目录 + `index.ts` 出口组织。

## 5. 前端 · 响应式外壳基座与验证（AC-9 基座）

- [x] 5.1 在 `shared/styles/tokens.css` 按外壳布局需要新增布局/断点类 token（不改既有语义色 token）；外壳与基元用 `min-width:0` + `overflow-wrap`/截断处理超长英文事件名/选项名。
- [x] 5.2 校验应用外壳与共享基元在 ≤430px 窄屏无横向滚动、无文本溢出（功能页具体窄屏布局归各自 change）。
- [x] 5.3 运行验证：`frontend/` 下 `pnpm typecheck` + `pnpm lint`（必要时 `pnpm test`）。
