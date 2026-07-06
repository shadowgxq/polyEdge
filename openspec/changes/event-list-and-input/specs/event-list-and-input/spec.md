## ADDED Requirements

### Requirement: 默认事件列表分类 Tab 与事件卡片

系统 SHALL 在 `/events` 页内提供「Polymarket 热门」与「世界杯赛事」两个分类 Tab，默认激活「热门」；切换 Tab SHALL 经 `GET /api/v1/events`（`category=hot|world_cup`）读取对应分类默认事件并以卡片列表渲染。每张事件卡片 MUST 展示事件名、各选项赔率（隐含概率）概览、事件级概览偏差标签与数据快照时间；概览偏差标签取接口返回的 `overview_label` 并标注 `overview_option_name`（即事件内 `|bias|` 最大选项的三分类标签 + 该选项名），`applicable=false`（不适用偏差分析）的事件 MUST 标注「不适用偏差分析」而非渲染偏差标签。偏差标签展示复用 `BiasLabel` 基元、快照时间复用 `SnapshotTime` 基元；卡片分类枚举与文案由接口/i18n 注入，前端不自算偏差。来源：PRD §4.1、AC-1、bias-algorithm §4、bias-algorithm §6。

#### Scenario: 默认落热门分类并渲染卡片

- **WHEN** 用户进入 `/events`
- **THEN** 默认激活「热门」Tab，经 `GET /api/v1/events?category=hot` 加载事件卡片
- **AND** 每张卡片展示事件名、各选项赔率、概览偏差标签（标注该选项名）与数据快照时间

#### Scenario: 切换到世界杯分类

- **WHEN** 用户点击「世界杯赛事」Tab
- **THEN** 经 `GET /api/v1/events?category=world_cup` 加载并渲染该分类卡片列表
- **AND** 分类切换不丢失已加载的另一分类交互状态归属

#### Scenario: 卡片概览标签标注最大偏差选项名

- **WHEN** 卡片的 `overview_label` 非空且 `applicable=true`
- **THEN** 卡片以 `BiasLabel` 渲染该三分类标签并同时标注 `overview_option_name`

#### Scenario: 事件不适用偏差分析

- **WHEN** 某事件 `applicable=false`（`overview_label` 为 null）
- **THEN** 卡片标注「不适用偏差分析」，仅展示事件名与原始选项赔率，不渲染偏差标签

### Requirement: 列表规模上限与加载更多

系统 SHALL 以接口返回的 `page` / `page_size` / `has_more` 约束列表规模，首屏不无限堆叠；当 `has_more=true` 时 SHALL 提供「加载更多」或分页入口按 `page+1` 追加请求，`has_more=false` 时 SHALL 不再展示加载入口。加载中与追加中 SHALL 有明确加载态，不表现为空白。来源：PRD §4.1。

#### Scenario: 存在更多时可加载更多

- **WHEN** 当前分类响应 `has_more=true`
- **THEN** 列表底部展示「加载更多」入口
- **AND** 触发后以 `page+1` 请求并把新事件追加到列表尾部

#### Scenario: 无更多时不展示加载入口

- **WHEN** 当前分类响应 `has_more=false`
- **THEN** 列表不展示「加载更多」入口

### Requirement: 手动事件输入之链接解析

系统 SHALL 提供手动输入区，用户粘贴 Polymarket 事件链接或 slug 后，前端 MUST 仅做 URL 形态校验（是否为合法 Polymarket 链接/slug 形态），形态非法时就地提示且不发起请求；形态合法时经 `POST /api/v1/events/resolve`（body `{ input }`）交后端提取 slug 并解析。slug 提取与有效性判定归后端（依赖后端接口 `POST /api/v1/events/resolve`），前端不自行解析 slug。解析成功 SHALL 定位到该事件并导航至其明细路由；解析不出（接口返回「未找到」错误态）SHALL 展示明确空态与重试引导，不静默失败。来源：PRD §4.2、AC-2、data-source §3。

#### Scenario: 前端仅做 URL 形态校验

- **WHEN** 用户输入的链接不符合 Polymarket 链接/slug 形态
- **THEN** 前端就地提示形态非法，不调用 `resolve` 接口

#### Scenario: 合法链接交后端解析并定位

- **WHEN** 用户提交形态合法的链接/slug
- **THEN** 经 `POST /api/v1/events/resolve` 解析，成功后导航到该事件的 `/events/:eventId` 明细

#### Scenario: 解析不出给明确空态

- **WHEN** `resolve` 返回「未找到」错误态
- **THEN** 展示「未找到该事件」空态与重试引导，不静默失败

### Requirement: 手动事件输入之名称搜索与本地回退标注

系统 SHALL 支持按事件名称搜索：经 `GET /api/v1/events/search`（`q`）返回候选列表供用户选择，选中候选 SHALL 定位到对应事件。搜索走后端（依赖后端接口 `GET /api/v1/events/search`）；当响应 `search_scope=local_cache`（后端本地模糊回退）时，前端 MUST 标注「仅在当前收录事件范围内搜索」。搜不到（`candidates` 为空）SHALL 展示明确空态与重试引导，不静默失败。来源：PRD §4.2、AC-2、data-source §3。

#### Scenario: 返回候选供选择

- **WHEN** 用户输入名称并搜索且 `candidates` 非空
- **THEN** 展示候选事件列表，选中某候选后定位到其 `/events/:eventId`

#### Scenario: 本地回退标注搜索范围

- **WHEN** 搜索响应 `search_scope=local_cache`
- **THEN** 在结果区标注「仅在当前收录事件范围内搜索」

#### Scenario: 搜不到给明确空态

- **WHEN** 搜索响应 `candidates` 为空数组
- **THEN** 展示「未搜到相关事件」空态与重试引导，不静默失败

### Requirement: 事件选定与导航

系统 SHALL 使三种输入方式（热门列表选、世界杯列表选、手动输入链接/名称）均能定位到唯一事件并导航到该事件的单事件明细路由 `/events/:eventId`（明细正文归 single-event-detail change）。列表卡片与候选项 SHALL 可点击进入明细，导航复用 web-app-shell-i18n 的路由契约。来源：PRD §4.0、PRD §4.2、AC-2。

#### Scenario: 从卡片进入明细

- **WHEN** 用户点击某事件卡片
- **THEN** 导航到该事件的 `/events/:eventId` 明细路由

#### Scenario: 三种输入方式均可定位单一事件

- **WHEN** 用户经列表选、世界杯选或手动输入任一方式选定事件
- **THEN** 均导航到唯一对应的单事件明细路由

### Requirement: 空态、错误态与重试

系统 SHALL 为列表与输入的各降级场景复用共享 `EmptyState` / `ErrorState` 基元，提供本地化说明与操作入口，不表现为空白或整页报错：世界杯 Tab 无匹配事件 SHALL 展示空态并引导切回热门 Tab；列表拉取失败 SHALL 展示错误态与重试；手动输入无法解析/搜不到 SHALL 展示空态与重试引导。服务端态（列表数据、降级标注、快照时间）经 TanStack Query 承载。来源：PRD §5.2、AC-5、data-source §3。

#### Scenario: 世界杯无匹配事件

- **WHEN** `world_cup` 分类返回空列表
- **THEN** 以 `EmptyState` 展示「当前无世界杯相关事件」并提供切回热门 Tab 的操作
- **AND** 不呈现空白列表

#### Scenario: 列表拉取失败可重试

- **WHEN** `GET /api/v1/events` 请求失败
- **THEN** 以 `ErrorState` 展示错误说明与重试入口
- **AND** 不静默失败、不整页报错

### Requirement: 只读无交易入口与窄屏响应式

系统 SHALL 保证事件列表与输入全流程只读，MUST NOT 出现任何交易/下单/钱包连接入口（AC-7）。列表页与卡片布局 SHALL 在 ≤430px 窄屏无横向滚动、无文本溢出，超长英文事件名/选项名按截断/换行处理；样式 SHALL 仅使用 `tokens.css` 的 token，不硬编码颜色/圆角/阴影。来源：AC-7、AC-9。

#### Scenario: 全流程无交易入口

- **WHEN** 用户在事件列表与输入流程中操作
- **THEN** 界面不出现任何交易、下单或连接钱包入口

#### Scenario: 430px 窄屏无横向溢出

- **WHEN** 视口宽度为 430px 或更窄
- **THEN** 列表页与事件卡片无横向滚动条，超长英文事件名/选项名按截断/换行呈现
