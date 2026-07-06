## ADDED Requirements

### Requirement: 两顶层 Tab 应用外壳

系统 SHALL 提供包含两个顶层视图 Tab 的应用外壳：「事件列表」与「偏差排行」，且首次进入 SHALL 默认落在「事件列表」。外壳 SHALL 为两 Tab 提供持久的顶层导航容器与内容 outlet；功能页正文由下游 change 填充，本能力只保证外壳与 Tab 切换。来源：PRD §4.0。

#### Scenario: 首次进入默认事件列表

- **WHEN** 访客首次进入首页
- **THEN** 顶层导航渲染「事件列表」与「偏差排行」两个 Tab
- **AND** 当前激活 Tab 为「事件列表」，其内容 outlet 可见

#### Scenario: 切换到偏差排行 Tab

- **WHEN** 访客点击「偏差排行」Tab
- **THEN** 激活 Tab 切换为「偏差排行」并渲染其内容 outlet
- **AND** 顶层导航保持可见，可切回「事件列表」

### Requirement: 单事件明细面包屑与回跳骨架

系统 SHALL 为单事件明细提供面包屑/返回入口，使明细页可回到来源列表；排行榜单项 SHALL 能回跳其所属单事件明细。本能力提供路由骨架与占位 outlet，明细/排行正文由下游 change 填充。来源：PRD §4.0。

#### Scenario: 从事件进入明细并可返回

- **WHEN** 访客从事件列表/排行进入某事件的单事件明细路由
- **THEN** 明细页渲染面包屑/返回入口
- **AND** 触发返回时回到来源列表视图

#### Scenario: 榜单项回跳单事件明细

- **WHEN** 访客在偏差排行中点击某条榜单项
- **THEN** 路由导航到该项所属事件的单事件明细

### Requirement: 应用装配与数据流基座

系统 SHALL 在 app providers 层装配全局 `QueryClient` 与 i18n Provider，使服务端状态（偏差结果、降级标注、数据快照时间）经 Query 缓存承载、界面偏好（语言）经本地状态承载。所有网络请求 SHALL 经 `shared/api` 的统一 `requestClient`，组件内不得直接发起请求。来源：PRD §1.4、§5.2。

#### Scenario: 全局 Provider 装配

- **WHEN** 应用启动挂载根节点
- **THEN** `QueryClientProvider` 与 i18n Provider 均已就位于 app providers 层
- **AND** 任意路由下的页面均可消费 Query 缓存与翻译

#### Scenario: 服务端状态经 Query 承载

- **WHEN** 页面需要读取偏差结果等服务端数据
- **THEN** 该数据经 `shared/api` service 调用并由 Query 缓存承载
- **AND** 组件内不出现对 axios/fetch 的直接调用

### Requirement: 窄屏响应式外壳基座

系统 SHALL 保证应用外壳（顶层导航、Tab、内容容器）在 ≤430px 窄屏无横向滚动、无文本溢出，超长文本按截断/换行处理；外壳布局 SHALL 仅使用 `tokens.css` 中的 token，不硬编码颜色/圆角/阴影/断点魔数。各功能页具体窄屏布局归各自 change。来源：PRD AC-9（基座）。

#### Scenario: 430px 窄屏无横向溢出

- **WHEN** 视口宽度为 430px 或更窄
- **THEN** 应用外壳无横向滚动条
- **AND** 顶层导航与 Tab 文本不溢出容器，超长文本按截断/换行呈现
