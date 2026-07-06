## Context

`web-app-shell-i18n` 已交付前端地基：`/events/:eventId` 路由骨架（含面包屑/返回、占位 outlet）、共享 UI 基元（`OptionMetricsRow`/`BiasLabel`/`SnapshotTime`/`EmptyState`/`ErrorState`，纯展示、分类与数值外部注入）、i18n 架构（en/zh、默认 en、市场内容不翻译的插值 key 约定、三分类标签 key `bias.label.hot|cold|fair` 口径取自 bias-algorithm §4）、`QueryClient` 装配与 `shared/api` service + `*.queries.ts` 消费模式。`analysis-api` 已定义单事件明细接口 `GET /api/v1/events/{slug}` → `EventDetail`（`options: OptionAnalysis[]`，含 `price/heat/bias_score/label{zh,en}/excluded`；`comment_count`；`applicable`；`degraded_trade_only`；`data_snapshot_at`），边界/降级为成功响应内的标注字段而非错误态。

本 change 前端单端，只填充 `/events/:eventId` 明细正文，消费上述基元与接口，不改二者已冻结的契约、不做偏差计算、不涉及后端。硬约束：样式只用 `tokens.css` token；请求只经 `shared/api` 的 `requestClient` 并经 Query 承载服务端态；route page 只做 composition/状态归属/编排，UI 区块下沉命名组件（遵循 file-organization / component-splitting）。

## Goals / Non-Goals

**Goals:**

- 填充单事件明细页正文：选项明细列表（赔率/热度/偏差评分/三分类标签）、按偏差评分排序、泡沫/冷门视觉区分。
- 落地边界/降级标注：`degraded_trade_only`（纯交易热度）、`applicable=false`（不适用偏差分析）、选项 `excluded`（已排除），全部来自接口标注字段，前端只展示。
- 事件级 `comment_count` 关注度标签 + `data_snapshot_at` 快照时间（`SnapshotTime` 基元）。
- 明细服务端态经 `shared/api` service + `*.queries.ts`（Query）承载，加载/空/错误态复用基元；面包屑/返回回到来源列表；只读无交易入口；≤430px 窄屏无溢出。

**Non-Goals:**

- 不做偏差计算（`bias_score`/`label`/`excluded`/`applicable`/`degraded_trade_only` 全由后端算好，前端消费）。
- 不改动 `web-app-shell-i18n` 的路由骨架/基元/i18n 契约与 `analysis-api` 的接口契约（只消费）。
- 不实现列表/输入页、排行页、分享出图、后端接口/迁移、外壳/i18n 地基本身。
- 不新增共享基元（若明细专有展示位不足，优先在页面私有子组件内组合既有基元，避免下沉污染 shared）。

## Decisions

### D1. 模块落 `pages/`（或既有页面模块目录）下的明细模块，route page 只做编排

单事件明细正文落在明细模块目录（复用 `web-app-shell-i18n` 预留的 `/events/:eventId` 页面位置），route page 组件只承担：读路由参数 `eventId`（即 slug）、调用明细 query、按加载/空/错误/成功分派、组织面包屑与选项列表区块的 composition 与状态归属。独立 UI 区块（选项列表、单个选项行封装、事件级关注度栏、边界标注条）下沉为该模块私有命名组件，不塞进 route page（遵循 CLAUDE.md「route page 只做 composition/状态归属/编排」与 component-splitting）。

- 备选：把列表渲染、排序、标注逻辑全写进 route page。放弃：违反 route page 职责边界、区块无法独立测试与复用。

### D2. 数据流：`*.api.ts`（调 `request`）+ `*.queries.ts`（`useQuery`），服务端态经 Query

在明细模块内新增 `*.api.ts` 调 `shared/api` 的 `request` 请求 `GET /api/v1/events/{slug}`，出参类型对齐 `analysis-api` 的 `EventDetail`/`OptionAnalysis`；`*.queries.ts` 用 `useQuery(['event-detail', slug])` 封装，沿用 `AppProviders` 里 `QueryClient` 的快照类默认项（`staleTime`/`retry`/`refetchOnWindowFocus`）。组件内不出现 axios/fetch 直调（CLAUDE.md 硬约束、PRD §5.2 状态归属）。slug 缺失/非法时不发请求，直接走空态。

- 备选：组件内直接 `useEffect + fetch`。放弃：违反统一 `requestClient` 与服务端态经 Query 的硬约束。

### D3. 边界/降级作为成功响应内标注驱动展示，前端不判定口径

`applicable` / `degraded_trade_only` / 选项 `excluded` 均为接口成功响应内的标注字段（`analysis-api` D7 / analysis-api-runtime「数据边界作为成功响应内标注」）。前端按字段驱动展示分支：

- `applicable=false` → 渲染「不适用偏差分析」标注 + 原始选项数据（不渲染 `BiasLabel`/偏差评分）。
- `degraded_trade_only=true` → 事件级渲染「纯交易热度」标注条，选项偏差仍按接口退化口径经 `OptionMetricsRow` 展示。
- 选项 `excluded=true` → 该行标注「已排除」，不渲染偏差评分/标签，且不参与排序。

前端 SHALL NOT 自行判断退化/排除/适用性（口径归 bias-algorithm §3.5/§6，后端已判定）。降级标注文案经 i18n 新增 key（沿用 `web-app-shell-i18n` 的 en/zh resource 组织与「市场内容不翻译、含市场内容句子用插值 key」约定）。

- 备选：前端按选项数据是否缺失再判一次退化。放弃：与后端口径漂移风险、违反「前端只展示」。

### D4. 三分类标签与偏差评分：直接消费接口 `label{zh,en}` 与 `bias_score`，经 `BiasLabel`/`OptionMetricsRow` 基元

选项分类来自后端 `label`（含 zh/en 两套，bias-algorithm §4 口径），前端按当前语言取对应文案注入 `BiasLabel`（基元入参 `category: 'hot'|'cold'|'fair'` 与文案）。`OptionMetricsRow` 收「已算好的」赔率（`price` 隐含概率）/热度（`heat`）/偏差评分（`bias_score`）/分类，基元做本地化数字格式，评分数值口径不变。分类枚举到 hot/cold/fair 的映射：接口若返回三分类枚举则直接映射；若仅返回 zh/en 文案则由 `bias_score` 相对阈值符号映射到基元 category（口径仍取自后端标签语义，前端只做展示映射）——实现阶段以 `analysis-api` 的 `OptionAnalysis.label` 实际结构为准，优先消费显式分类枚举避免二次判定。

### D5. 排序：展示层受控重排，默认按 |bias_score| 或 bias_score 呈现泡沫→冷门

排序为纯前端展示态（`useState` 排序键），不改任何选项数值，被 `excluded` 的选项固定置底且不参与排序权重。默认排序呈现偏差最显著的选项在前（便于「泡沫风险首屏可见」，PRD §1.2 目标口径），具体默认键在实现时对齐设计走查；`applicable=false` 时不提供排序（无偏差评分）。

## Risks / Trade-offs

- [`OptionAnalysis.label` 到基元 `category` 的映射方式取决于 `analysis-api` 出参结构（显式枚举 vs 仅 zh/en 文案）] → D4 约定优先消费显式分类枚举，缺枚举时按 `bias_score` 相对阈值符号映射；实现阶段以接口实际 schema 为准，映射集中一处便于对齐。
- [依赖 `web-app-shell-i18n` 基元 props 与 `/events/:eventId` outlet 契约，若上游未落地或 props 调整会返工] → 依赖二者已冻结 spec 契约（handoff `depends_on`）；基元只收展示数据、明细页不改基元；集成期只在页面侧适配。
- [降级标注 i18n 措辞与 bias-algorithm §3.5 口径需一致] → 标注文案 key 在明细模块新增并对齐 bias-algorithm §3.5/§6 语义，复用 shell 的 resource 组织，不硬编码拼接市场内容。
- [窄屏下多列指标行 + 长英文选项名易横向溢出] → 依赖 `OptionMetricsRow` 基元自身窄屏处理 + 页面容器 `min-width:0`/`overflow-wrap`，仅用 tokens.css 布局 token（AC-9）。

## Migration Plan

- 纯新增：在明细模块新增 route page 正文组件、私有子组件、`*.api.ts`/`*.queries.ts`、i18n 降级/关注度标注 key，替换 `web-app-shell-i18n` 预留的 `/events/:eventId` 占位 outlet 内容。
- 回滚：恢复占位 outlet 即可，无数据副作用、无迁移。
- 集成顺序：依赖 `web-app-shell-i18n`（路由/基元/i18n）与 `analysis-api`（明细接口）先落地；本 change 对接其已交付契约。

## Open Questions

- `OptionAnalysis` 是否含显式三分类枚举字段，决定 D4 映射走枚举直连还是 `bias_score` 符号映射——以 `analysis-api` 实际出参为准，不阻塞骨架。
- 默认排序键（`bias_score` 降序 vs `|bias_score|` 降序）与排序交互形态（切换/固定）在实现阶段对齐设计走查，不改口径。
