## Why

PRD §4.0（信息架构与导航）、§4.6 / §5.4（多语言）与 AC-8 / AC-9 规定：产品需要「事件列表 / 偏差排行」两顶层 Tab 的外壳、可回跳的单事件明细导航、中英可切换且刷新保持的 i18n，以及 ≤430px 无横向溢出的响应式基座。当前仓库只有一个占位 `HomePage`，没有承载这些的应用外壳、路由/IA、i18n 基建与共享偏差展示基元。下游功能页（`event-list-and-input` / `single-event-detail` / `bias-ranking` / `share-poster`）都要复用这套地基，因此先把外壳、i18n、共享 UI 基元与数据层装配沉淀为可独立验收的前端 capability，避免各页各自造轮子导致 IA、文案、状态承载不一致。

## What Changes

- 搭建应用外壳与路由/IA（PRD §4.0）：两顶层 Tab（事件列表 / 偏差排行），默认进入事件列表；提供单事件明细的面包屑/返回骨架与「榜单项 → 单事件明细」回跳路由约定。功能页正文由下游 change 填充，本 change 只落 route 骨架 + 占位 outlet。
- 建立 i18n 基建（PRD §4.6 / §5.4、AC-8）：接入 `i18next` + `react-i18next`，English + 中文两套 resource、默认 English、语言切换入口、`localStorage` 持久化（刷新保持）；约定「含市场内容的句子一律用带占位符插值 key，事件名/选项名作为不翻译变量注入」；内置偏差三分类标签中英文案（bias-algorithm §4）。
- 沉淀共享偏差展示基元（PRD §4.3 / §4.4，供列表/明细/排行/分享复用）：偏差标签（hot/cold/fair 三分类 chip）、选项指标行（赔率/热度/偏差评分）、数据快照时间标注；以及空态 / 错误态通用组件（PRD §5.2 各降级态复用）。基元只做纯展示，数值口径由上游算好后注入。
- 装配数据层基座（PRD §1.4 / §5.2 状态归属）：在 app providers 配置 `QueryClient`（服务端状态：偏差结果 / 降级标注 / 快照时间经 Query 缓存承载）并接入 i18n Provider；约定 `shared/api` service 层调用模式（一律经 `requestClient`），语言等界面偏好经本地状态（`localStorage`）承载。
- 落地响应式基座（AC-9 基座）：基于 `tokens.css` 补齐外壳级布局 token/断点约定，保证外壳与共享基元在 ≤430px 窄屏无横向溢出、超长英文文本截断/换行；不含各功能页具体窄屏布局（归各自 change）。

## Capabilities

### New Capabilities
- `web-app-shell`: 应用外壳与信息架构导航——两顶层 Tab 路由（默认事件列表）、单事件明细面包屑/返回与榜单回跳的路由骨架、app providers 装配（`QueryClient` + i18n Provider）、`shared/api` service/Query 数据流约定，以及 ≤430px 响应式外壳基座（PRD §4.0、§1.4、§5.2、AC-9 基座）。
- `i18n`: 国际化基建——English + 中文两语言、默认 English、切换入口、`localStorage` 持久化、含市场内容句子的占位符插值 key 约定、偏差三分类标签中英两套文案（PRD §4.6 / §5.4、AC-8、bias-algorithm §4）。
- `shared-ui-primitives`: 共享偏差展示基元与状态组件——偏差标签、选项指标行、数据快照时间标注、空态 / 错误态组件，纯展示、口径外部注入，供列表/明细/排行/分享四页复用（PRD §4.3 / §4.4 / §5.2 / §5.3）。

### Modified Capabilities
<!-- 无：greenfield，openspec/specs/ 下暂无既有 capability。 -->

## Impact

- 新增 `frontend/` 代码，复用既有 `app/` `pages/` `shared/` 分层，不另起平行结构：
  - `app/router/`：两顶层 Tab 路由 + 单事件明细/榜单回跳骨架（占位 outlet）。
  - `app/providers/`：`QueryClient` 配置默认项 + i18n Provider 装配。
  - `shared/i18n/`（新增子目录）：i18next 初始化、en/zh resource、语言持久化、插值 key 约定与三分类标签文案。
  - `shared/ui/`：偏差标签、选项指标行、快照时间标注、空态/错误态等无业务基元。
  - `shared/styles/tokens.css`：仅按外壳级布局需要补充断点/布局 token，不改既有语义色 token。
- 依赖已在 `package.json`：`i18next` / `react-i18next` / `i18next-browser-languagedetector` / `react-router-dom` / `@tanstack/react-query` / `zustand`，无需新增第三方依赖。
- 无后端改动、无接口、无迁移：本 change 为前端单端地基。
- 为下游预留：`web-app-shell` 的 route 骨架与 outlet、`i18n` 的 resource/插值约定与标签 key、`shared-ui-primitives` 的基元 props 契约，供 `event-list-and-input` / `single-event-detail` / `bias-ranking` / `share-poster` 直接消费。
