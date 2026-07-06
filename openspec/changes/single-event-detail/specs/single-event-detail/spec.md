## ADDED Requirements

### Requirement: 单事件明细选项列表展示

系统 SHALL 在单事件明细页列出该事件全部选项；对每个可分析选项经共享 `OptionMetricsRow` 基元展示赔率（隐含概率）、热度、偏差评分与三分类 `BiasLabel`，三分类标签口径与 bias-algorithm §4 一致，前端只展示已算好的分类与文案、SHALL NOT 在前端重算 `bias_i` 或阈值。选项数据来源为 `analysis-api` 的 `GET /api/v1/events/{slug}` 明细响应（`options: OptionAnalysis[]`）。样式 SHALL 仅用 `tokens.css` 的 token。来源：PRD §4.3、AC-3、bias-algorithm §4。

#### Scenario: 展示每个可分析选项四要素

- **WHEN** 明细接口返回某事件的可分析选项集合
- **THEN** 页面为每个未被排除的选项渲染一行 `OptionMetricsRow`，呈现赔率（隐含概率）、热度、偏差评分与三分类偏差标签

#### Scenario: 前端不重算偏差

- **WHEN** 渲染偏差评分与三分类标签
- **THEN** 页面直接消费接口返回的 `bias_score` 与 `label{zh,en}`，不在前端计算 `bias_i` 或分类阈值

### Requirement: 按偏差评分排序与泡沫/冷门视觉区分

系统 SHALL 支持将选项按偏差评分排序，并使泡沫风险（hot）与冷门机会（cold）选项在明细区有明显视觉区分（沿用 `tokens.css` 的 hot/cold/fair 信号色语义，经 `BiasLabel` 基元呈现）。排序为纯展示层重排，SHALL NOT 改变任一选项的偏差评分或分类口径。来源：PRD §4.3、AC-3、bias-algorithm §4。

#### Scenario: 按偏差评分排序

- **WHEN** 用户在明细页触发按偏差评分排序
- **THEN** 选项列表按偏差评分重新排列，各选项的偏差评分与分类保持不变

#### Scenario: 泡沫与冷门视觉区分

- **WHEN** 选项集合中同时存在 hot 与 cold 分类选项
- **THEN** hot 选项以泡沫风险信号色、cold 选项以冷门机会信号色呈现，二者视觉上明显可区分

### Requirement: 纯交易热度退化标注

系统 SHALL 在明细接口返回 `degraded_trade_only=true`（全事件退化为纯交易热度）时，于明细页明确标注「纯交易热度」降级态，其偏差结果仍按接口返回的退化口径展示，SHALL NOT 表现为空白或静默省略。降级文案经 i18n 且不翻译市场内容。来源：PRD §5.2、bias-algorithm §3.5、AC-5。

#### Scenario: 全事件退化标注

- **WHEN** 明细接口返回 `degraded_trade_only=true`
- **THEN** 明细页展示「纯交易热度」降级标注，并按接口返回的退化口径展示各选项偏差

### Requirement: 不适用偏差分析标注

系统 SHALL 在明细接口返回 `applicable=false`（事件仅单一有效选项或缺价格）时，标注「不适用偏差分析」并仅展示原始选项数据，SHALL NOT 展示偏差评分或三分类标签。来源：PRD §5.2、bias-algorithm §6、AC-5。

#### Scenario: 事件不适用偏差分析

- **WHEN** 明细接口返回 `applicable=false`
- **THEN** 明细页标注「不适用偏差分析」并仅展示原始选项数据，不呈现偏差评分与三分类标签

### Requirement: 被排除选项标注

系统 SHALL 在某选项 `excluded=true`（价格全为 0 或数据缺失被排除出偏差计算）时，于列表中标注该选项已排除，其余有效选项的偏差按接口返回的重归一结果展示；被排除选项 SHALL NOT 参与排序权重且不呈现偏差标签。来源：PRD §5.2、bias-algorithm §6。

#### Scenario: 选项已排除标注

- **WHEN** 明细接口某选项返回 `excluded=true`
- **THEN** 该选项行标注「已排除」且不呈现偏差评分与三分类标签，其余有效选项正常呈现接口返回的偏差结果

### Requirement: 事件级关注度与数据快照时间

系统 SHALL 在明细页展示事件级 `comment_count` 关注度标签（不参与单选项偏差），并经共享 `SnapshotTime` 基元以本地化时间格式标注该数据的快照时间（`data_snapshot_at`）。来源：PRD §4.3、§5.3。

#### Scenario: 展示事件关注度与快照时间

- **WHEN** 明细接口返回 `comment_count` 与 `data_snapshot_at`
- **THEN** 明细页展示事件级关注度标签与本地化的「数据快照时间」标注

### Requirement: 明细数据加载与降级态

系统 SHALL 经 `shared/api` service + TanStack Query 承载明细服务端态（偏差结果、降级标注、快照时间），组件内 SHALL NOT 直接发起 axios/fetch 请求。加载中呈现加载态；接口错误（含上游不可用）呈现 `ErrorState` 基元并提供重试；接口返回空事件时呈现 `EmptyState` 基元并引导返回来源列表，SHALL NOT 静默失败或整页报错。来源：PRD §5.2、§1.4、AC-5。

#### Scenario: 明细数据经 Query 承载

- **WHEN** 明细页需要读取某 slug 的事件明细
- **THEN** 数据经 `shared/api` service 调用并由 Query 缓存承载，组件内不出现对 axios/fetch 的直接调用

#### Scenario: 拉取失败呈现重试

- **WHEN** 明细接口返回错误态（如上游不可用）
- **THEN** 页面呈现 `ErrorState` 基元与本地化错误说明及重试入口，不整页报错

### Requirement: 面包屑返回与只读约束

系统 SHALL 在单事件明细页（路由 `/events/:eventId`）渲染面包屑/返回入口，触发返回时回到来源列表视图；页面 SHALL 全程只读，SHALL NOT 提供任何交易/下单/钱包连接入口。来源：PRD §4.0、AC-7。

#### Scenario: 经面包屑返回来源列表

- **WHEN** 用户在明细页触发面包屑/返回
- **THEN** 路由回到来源列表视图（事件列表或排行）

#### Scenario: 全程只读无交易入口

- **WHEN** 用户浏览单事件明细页
- **THEN** 页面不呈现任何交易/下单/钱包连接入口

### Requirement: 窄屏无溢出与超长文本处理

系统 SHALL 保证单事件明细页在 ≤430px 窄屏无横向滚动、无文本溢出，超长英文事件名/选项名按截断/换行/省略处理；布局 SHALL 仅使用 `tokens.css` 的 token，不硬编码颜色/圆角/阴影/断点魔数。来源：PRD §4.3、AC-9。

#### Scenario: 430px 窄屏无横向溢出

- **WHEN** 视口宽度为 430px 或更窄
- **THEN** 明细页无横向滚动条，选项行内超长事件名/选项名按截断/换行呈现且不溢出容器
