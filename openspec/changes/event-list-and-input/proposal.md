## Why

polyEdge 首页需要让用户在「事件列表」Tab 内浏览 Polymarket 热门与世界杯两类默认事件，并支持粘贴链接 / 输入名称定位任一事件（PRD §4.1/§4.2、AC-1/AC-2）。web-app-shell-i18n 已提供路由 outlet（`/events`）、共享 UI 基元与 i18n/Query 地基，analysis-api 已冻结 `GET /api/v1/events`、`POST /api/v1/events/resolve`、`GET /api/v1/events/search` 三个接口契约；本 change 填充 `/events` 页面正文与事件输入交互，把这些地基与接口拼成可用的列表与输入闭环。

## What Changes

- 新增 `/events` 事件列表页正文：热门 / 世界杯两分类 Tab，事件卡片展示事件名 + 各选项赔率概览 + 事件级概览偏差标签（取事件内 `|bias|` 最大选项标签并标注该选项名）+ 数据快照时间；不适用偏差分析的事件标注「不适用」（PRD §4.1、AC-1）。
- 新增列表规模上限与「加载更多」/分页交互：消费接口 `page`/`page_size`/`has_more`，超出上限不在首屏无限堆叠（PRD §4.1、建议 20/页）。
- 新增手动事件输入：前端仅做 Polymarket 链接 URL 形态校验后调 `resolve`；名称走 `search` 返回候选供选择；本地回退时标注「仅在当前收录事件范围内搜索」（PRD §4.2、AC-2、data-source §3）。
- 新增各降级空态 / 错误态：世界杯无匹配事件、手动输入无法解析 / 搜不到、列表拉取失败重试，均复用共享空态/错误态基元，不静默失败（PRD §5.2、AC-5 前端侧）。
- 全流程只读、无交易入口（AC-7）；≤430px 窄屏无横向滚动、超长英文名截断 / 换行（AC-9）。
- 新增该模块的 `shared/api` service（`*.api.ts`）+ `*.queries.ts`（TanStack Query），事件选定结果导航到 `/events/:eventId`（明细正文归 single-event-detail change）。

## Capabilities

### New Capabilities

- `event-list-and-input`: 事件列表页（热门/世界杯分类 Tab、事件卡片、规模上限与加载更多）与事件输入（列表选 / 手动输入链接或名称、前端 URL 形态校验、搜索候选选择、本地回退标注、各空态与重试）的前端能力。

### Modified Capabilities

<!-- 无：本 change 不改动既有 capability 的 requirements，仅消费 web-app-shell-i18n 的路由 outlet/基元与 analysis-api 的接口契约。 -->

## Impact

- 前端 `frontend/`：新增 `pages/events/`（列表页 route page + 私有组件）与其模块内 `*.api.ts` / `*.queries.ts` / `*.types.ts`；替换 web-app-shell-i18n 在 `/events` 预留的占位组件。
- 消费 web-app-shell-i18n 的 `AppShell` outlet、`BiasLabel` / `OptionMetricsRow` / `SnapshotTime` / `EmptyState` / `ErrorState` 基元、i18n 插值 key 约定、`QueryClient` + `shared/api` service 模式。
- 消费 analysis-api 的 `GET /api/v1/events`、`POST /api/v1/events/resolve`、`GET /api/v1/events/search`（依赖后端接口，本 change 不实现后端）。
- 不涉及后端、数据库、迁移；不涉及单事件明细正文、排行页、外壳/i18n 地基本身。
