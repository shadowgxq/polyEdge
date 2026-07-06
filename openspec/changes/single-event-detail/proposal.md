## Why

用户从事件列表/排行进入某个 Polymarket 事件后，需要一个只读的单事件偏差明细页，把该事件全部选项的赔率（隐含概率）、热度、偏差评分与三分类标签一屏看清，并明确区分泡沫风险与冷门机会（PRD §4.3、AC-3）。当前 `web-app-shell-i18n` 只提供了 `/events/:eventId` 路由骨架与占位 outlet、共享 UI 基元与 i18n 契约，明细正文尚未填充；`analysis-api` 已定义 `GET /api/v1/events/{slug}` 明细契约。本 change 负责填充明细页正文，消费外壳基元与后端明细接口，落地降级/边界标注与窄屏只读体验。

## What Changes

- 在 `/events/:eventId` 路由填充单事件明细正文：面包屑/返回入口回到来源列表（PRD §4.0），只读、无任何交易入口（AC-7）。
- 展示事件全部选项，每个可分析选项经共享 `OptionMetricsRow` 基元呈现赔率（隐含概率）、热度、偏差评分、三分类 `BiasLabel`（口径 bias-algorithm §4，前端只展示不计算）。
- 支持按偏差评分排序，泡沫风险与冷门机会选项有明显视觉区分（PRD §4.3、AC-3）。
- 数据完整度与边界标注（消费 `analysis-api` 明细响应字段）：`applicable=false` 标注「不适用偏差分析」仅展示原始选项数据；`degraded_trade_only` 仅作为结果口径字段消费，不额外展示事件级提示；选项 `excluded` 仅作为前端过滤信号，不进入明细展示（PRD §5.2、bias-algorithm §3.5/§6）。
- 事件级 `comment_count` 关注度标签（不参与单选项偏差）与数据快照时间（`SnapshotTime` 基元，PRD §4.3/§5.3）。
- 明细数据经 `shared/api` service + `*.queries.ts`（TanStack Query）承载服务端态，加载/空态/错误态复用 `EmptyState`/`ErrorState` 基元（PRD §5.2、AC-5）。
- 窄屏 ≤430px 无横向溢出、超长英文事件名/选项名截断/换行（AC-9）。

## Capabilities

### New Capabilities
- `single-event-detail`: 单事件偏差明细页正文——选项明细列表（赔率/热度/偏差评分/三分类标签）、按偏差排序、泡沫/冷门视觉区分、不适用偏差分析边界标注、事件级 comment_count、数据快照时间、面包屑/返回，消费外壳路由与 UI 基元、`analysis-api` 明细接口。

### Modified Capabilities
<!-- 无：不改动 web-app-shell-i18n / analysis-api 已冻结的 requirement，仅消费其契约。 -->

## Impact

- 前端单端：`frontend/src/` 下新增单事件明细模块（页面正文组件 + `*.api.ts`/`*.queries.ts` + 私有子组件），填充 `web-app-shell-i18n` 预留的 `/events/:eventId` 占位 outlet。
- 消费依赖：`web-app-shell-i18n`（路由 `/events/:eventId`、面包屑/返回、`OptionMetricsRow`/`BiasLabel`/`SnapshotTime`/`EmptyState`/`ErrorState` 基元、i18n 插值 key 与三分类标签 `bias.label.hot|cold|fair`、QueryClient/service 模式）、`analysis-api`（`GET /api/v1/events/{slug}` → EventDetail）。
- 不涉及后端接口/迁移、不涉及列表/排行/分享页、不涉及外壳/i18n 地基本身。
- 硬约束：样式只用 `tokens.css` token；请求只经 `shared/api` 的 `requestClient`，服务端态经 Query；route page 只做 composition/状态归属/编排，UI 区块下沉命名组件。
