## ADDED Requirements

### Requirement: 偏差排行三榜展示

系统 SHALL 在 `/ranking` 顶层 Tab 正文按当前分类（`hot` / `world_cup`）消费后端 `GET /api/v1/rankings`，展示三榜：泡沫风险榜（`bubble`）、冷门机会榜（`underhyped`）、合理列表（`fair`）。前端 SHALL 按后端返回的顺序渲染各榜榜单项，不在前端重新分档、排序或截取 TopN（三榜互斥无交集、泡沫降序 / 冷门升序、TopN 截取均由后端保证）。数据经 `shared/api` `requestClient` 调用并由 Query 缓存承载，组件内不直接发请求。来源：PRD §4.4、AC-4、bias-algorithm §5。

#### Scenario: 按当前分类展示三榜

- **WHEN** 访客进入偏差排行 Tab 且排行接口成功返回
- **THEN** 页面渲染泡沫风险榜、冷门机会榜、合理列表三榜
- **AND** 各榜榜单项按后端返回顺序展示，前端不重新排序或截取

#### Scenario: 数据经统一请求客户端与 Query 承载

- **WHEN** 页面读取排行数据
- **THEN** 该数据经 `shared/api` `requestClient` 调用并由 Query 缓存承载
- **AND** 组件内不出现对 axios/fetch 的直接调用

### Requirement: 榜单项事件归属与偏差展示

系统 SHALL 使每条榜单项展示其所属事件（事件标题）、选项名、赔率（隐含概率）、偏差评分，以及三分类偏差标签。偏差标签 SHALL 复用共享 `BiasLabel` 基元，按榜别映射三分类（`bubble → hot` / `underhyped → cold` / `fair → fair`）注入 `category`，视觉与文案统一走基元与 `tokens.css` 信号色，SHALL NOT 在前端重新计算偏差或分类。来源：PRD §4.4、AC-4、bias-algorithm §4/§5。

#### Scenario: 榜单项呈现事件与选项四要素

- **WHEN** 渲染任一榜单项
- **THEN** 该项展示所属事件标题、选项名、赔率、偏差评分与偏差标签

#### Scenario: 偏差标签按榜别映射三分类

- **WHEN** 渲染泡沫风险榜 / 冷门机会榜 / 合理列表中的榜单项
- **THEN** 偏差标签分别以 hot / cold / fair 分类经 `BiasLabel` 基元渲染对应信号色与当前语言文案
- **AND** 前端不重新计算 `bias_i` 或分类阈值

### Requirement: 榜单项回跳单事件明细

系统 SHALL 使每条榜单项可点击回跳其所属事件的单事件明细路由 `/events/:eventId`（以 `event_slug` 作为路由参数），复用应用外壳的回跳契约。回跳入口 SHALL 键盘可达并带可读的 `aria-label`（含事件名/选项名，经 i18n 插值，不字符串拼接）。来源：PRD §4.4、AC-4、PRD §4.6。

#### Scenario: 点击榜单项回跳明细

- **WHEN** 访客点击某条榜单项
- **THEN** 路由导航到该项 `event_slug` 对应的 `/events/:eventId` 单事件明细

#### Scenario: 回跳入口键盘可达且有可读标签

- **WHEN** 榜单项回跳入口获得键盘焦点
- **THEN** 该入口可用键盘触发导航
- **AND** 其 `aria-label` 以 i18n 插值呈现所属事件名与选项名，不由字符串拼接得到

### Requirement: 各榜独立空态与页面加载/错误态

系统 SHALL 分离处理三种状态：加载中呈现加载态；拉取失败呈现错误态（复用 `ErrorState` 基元）并提供重试入口；成功后某榜为空数组时该榜位单独呈现空态（复用 `EmptyState` 基元）而其余两榜正常渲染。降级 MUST NOT 表现为空白或整页报错。所有状态文案经 i18n。来源：PRD §5.2、AC-5。

#### Scenario: 某榜为空其余两榜正常

- **WHEN** 排行接口成功返回但某一榜为空数组
- **THEN** 该榜位呈现本地化空态说明
- **AND** 其余两榜正常渲染榜单项，页面不整体报错

#### Scenario: 拉取失败呈现可重试错误态

- **WHEN** 排行接口拉取失败
- **THEN** 页面呈现本地化错误说明与重试入口
- **AND** 触发重试重新拉取，不静默失败、不整页崩溃

#### Scenario: 加载中呈现加载态

- **WHEN** 排行数据正在拉取
- **THEN** 页面呈现加载态占位，而非空白

### Requirement: 窄屏三榜分段布局与只读展示

系统 SHALL 在 ≤430px 窄屏采用卡片纵向排列 + 三榜分段 Tab 切换（泡沫 / 冷门 / 合理三段）呈现排行，避免三榜横向溢出；宽屏可三榜并列分区。超长英文事件名/选项名 SHALL 截断/换行处理，页面无横向滚动。布局 SHALL 仅使用 `tokens.css` 的 token。全页 SHALL 只读，MUST NOT 提供任何交易/下单/钱包入口。来源：PRD §4.4、AC-9、AC-7。

#### Scenario: 窄屏三榜分段无横向溢出

- **WHEN** 视口宽度为 430px 或更窄
- **THEN** 排行以三榜分段 Tab + 卡片纵向排列呈现，页面无横向滚动
- **AND** 超长事件名/选项名按截断/换行呈现

#### Scenario: 全流程只读无交易入口

- **WHEN** 访客浏览排行页任一榜单项
- **THEN** 页面仅提供回跳单事件明细的只读入口
- **AND** 不出现任何交易、下单或钱包连接入口
