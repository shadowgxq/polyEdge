# Tasks

> 前端单端 change。数据依赖后端接口 `GET /api/v1/events/{slug}` → `EventDetail`（由 `analysis-api` 提供），本 change 只消费不实现。首次编辑前端代码前先读 docs/frontend/standards/frontend-development.md、components/components.md、components/component-splitting.md、standards/file-organization.md。

## 前端

### 1. 明细数据层（消费后端接口）

- [x] 1.1 在明细模块新增 `*.api.ts`，经 `shared/api` 的 `request` 调用 `GET /api/v1/events/{slug}`；定义/对齐出参类型 `EventDetail`（`options: OptionAnalysis[]` 含 `price/heat/bias_score/label{zh,en}/excluded`；`comment_count`；`applicable`；`degraded_trade_only`；`data_snapshot_at`）。**依赖后端接口 `GET /api/v1/events/{slug}`（analysis-api）**
- [x] 1.2 新增 `*.queries.ts`，用 `useQuery(['event-detail', slug])` 封装明细请求，沿用 `AppProviders` 的 `QueryClient` 快照类默认项；slug 缺失/非法时不发请求。组件内不出现 axios/fetch 直调（spec：明细数据经 Query 承载）。

### 2. 明细页正文与 route page 编排

- [x] 2.1 填充 `/events/:eventId` route page：读路由参数 `eventId`（slug）、调用 1.2 的 query、按 加载/空/错误/成功 分派，仅做 composition/状态归属/编排（spec：面包屑返回与只读约束；design D1）。
- [x] 2.2 渲染面包屑/返回入口（复用 `web-app-shell-i18n` 骨架），触发返回回到来源列表；确认全页只读、无任何交易/下单/钱包入口（spec：面包屑返回与只读约束，PRD §4.0/AC-7）。
- [x] 2.3 加载态呈现加载占位；错误态（含上游不可用）渲染 `ErrorState` 基元 + 重试；空事件渲染 `EmptyState` 基元并引导返回来源列表（spec：明细数据加载与降级态，PRD §5.2/AC-5）。

### 3. 选项明细列表与排序

- [x] 3.1 下沉私有「选项列表」区块组件，对每个未排除选项渲染 `OptionMetricsRow` 基元，注入已算好的赔率（`price` 隐含概率）/热度（`heat`）/偏差评分（`bias_score`）/分类；分类经 `BiasLabel` 基元按当前语言取 `label{zh,en}` 呈现，前端不重算 `bias_i`（spec：单事件明细选项列表展示，bias-algorithm §4）。
- [x] 3.2 实现展示层排序（`useState` 排序键），按偏差评分重排，不改任一选项数值；`excluded` 选项固定置底且不参与排序；`applicable=false` 时不提供排序（spec：按偏差评分排序与泡沫/冷门视觉区分；design D5）。
- [ ] 3.3 通过 `BiasLabel` 的 hot/cold/fair 信号色令泡沫风险与冷门机会选项明显视觉区分，样式只用 `tokens.css` token（spec：泡沫/冷门视觉区分，AC-3）。

### 4. 边界/降级标注（消费接口标注字段）

- [x] 4.1 `applicable=false` 分支：渲染「不适用偏差分析」标注 + 原始选项数据，不渲染偏差评分/`BiasLabel`（spec：不适用偏差分析标注，PRD §5.2/bias-algorithm §6）。
- [x] 4.2 `degraded_trade_only=true` 分支：事件级渲染「纯交易热度」标注条，选项偏差仍按接口退化口径经 `OptionMetricsRow` 展示（spec：纯交易热度退化标注，bias-algorithm §3.5）。
- [x] 4.3 选项 `excluded=true` 分支：该行标注「已排除」，不渲染偏差评分/标签（spec：被排除选项标注，bias-algorithm §6）。
- [x] 4.4 新增上述边界/降级标注的 i18n key（en/zh），复用 `web-app-shell-i18n` resource 组织；含市场内容的句子用占位符插值 key，事件名/选项名作变量注入不翻译（i18n 约定，PRD §4.6）。

### 5. 事件级关注度与快照时间

- [x] 5.1 下沉「事件级信息」区块：展示 `comment_count` 关注度标签（不参与单选项偏差），经 `SnapshotTime` 基元本地化标注 `data_snapshot_at`（spec：事件级关注度与数据快照时间，PRD §4.3/§5.3）。

### 6. 窄屏与验证

- [x] 6.1 明细页容器 ≤430px 窄屏无横向溢出，长英文事件名/选项名截断/换行，仅用 `tokens.css` 布局 token（spec：窄屏无溢出与超长文本处理，AC-9）。
- [x] 6.2 在 `frontend/` 下运行 `pnpm typecheck` + `pnpm lint`（必要时 `pnpm test`）；如缺依赖/脚本/授权无法执行则在交付说明中标注。
