<!-- 本 change 为前端单端（frontend/），全部任务属 ## 前端 范围；无后端分节。依赖后端接口由 analysis-api 提供，本 change 不实现后端。 -->

## 前端

### 1. 模块与数据层（PRD §4.1/§4.2、design D1/D2/D3）

- [x] 1.1 新建 `pages/events/` 模块骨架（目录 + `index.ts` 出口），替换 web-app-shell-i18n 在 `/events` 路由的占位组件引用为 `EventsPage`
- [x] 1.2 在 `pages/events/events.types.ts` 按 analysis-api 契约定义 TS 类型：`EventCard`（slug/title/options:[{name,price}]/overview_label:{zh,en}|null/overview_option_name|null/applicable/data_snapshot_at）、`EventListData`（category/items/has_more）、`EventSearchData`（candidates:[{slug,title}]/search_scope:'upstream'|'local_cache'）、`EventCategory`（'hot'|'world_cup'）
- [x] 1.3 在 `pages/events/events.api.ts` 用 `shared/api` 的 `request` 封装三个调用；**依赖后端接口 `GET /api/v1/events`（query category/page/page_size）、`POST /api/v1/events/resolve`（body {input}）、`GET /api/v1/events/search`（query q/limit）**，不在组件内直接发请求
- [x] 1.4 在 `pages/events/events.queries.ts` 封装：列表 `useInfiniteQuery`（queryKey `['events',category]`，`getNextPageParam` 依 `has_more` 取 `page+1`）、名称搜索受控 `useQuery`（queryKey `['events','search',q]`，`enabled` 依提交）、链接解析 `useMutation`（成功后导航）

### 2. 分类列表与事件卡片（PRD §4.1、AC-1、bias-algorithm §4/§6、design D5）

- [x] 2.1 实现 `EventCategoryTabs`：热门 / 世界杯分段 Tab，默认激活热门，窄屏用分段控件不横向溢出；切换驱动 `useInfiniteQuery` 的 `category`
- [x] 2.2 实现 `EventCard`：展示事件名 + 各选项赔率（隐含概率）概览 + 数据快照时间（复用 `SnapshotTime` 基元）；`applicable=true` 时用 `BiasLabel` 渲染 `overview_label` 并标注 `overview_option_name`
- [x] 2.3 `EventCard` 不适用分支：`applicable=false`（`overview_label=null`）时标注「不适用偏差分析」i18n 文案，仅展示原始选项赔率，不渲染 `BiasLabel`
- [x] 2.4 实现 `EventCardList`：渲染卡片列表 + 「加载更多」入口（`has_more=true` 时展示，触发 `fetchNextPage`；`has_more=false` 隐藏）+ 加载/追加加载态（不空白）
- [x] 2.5 卡片点击导航到 `/events/:eventId`（复用 web-app-shell-i18n 路由契约），明细正文归 single-event-detail change

### 3. 事件输入（PRD §4.2、AC-2、data-source §3、design D4）

- [x] 3.1 实现 `EventInputPanel`：链接输入做纯前端 URL 形态校验（Polymarket 事件链接/slug 形态正则），形态非法就地提示且不发请求；形态合法调 `resolve` mutation。**依赖后端接口 `POST /api/v1/events/resolve`（后端提取 slug + 有效性判定）**
- [x] 3.2 `resolve` 成功后导航到 `/events/:eventId`（用返回 `data.slug`）；返回「未找到」错误态时展示空态 + 重试引导（复用 `EmptyState`）
- [x] 3.3 实现名称搜索：输入名称调 `search` 受控 query。**依赖后端接口 `GET /api/v1/events/search`（含本地模糊回退）**
- [x] 3.4 实现 `EventSearchResults`：渲染候选列表（选中定位到 `/events/:eventId`）；`search_scope==='local_cache'` 时标注「仅在当前收录事件范围内搜索」i18n 文案；`candidates` 为空展示空态 + 重试引导

### 4. 空态 / 错误态与降级（PRD §5.2、AC-5、design D5）

- [x] 4.1 世界杯分类 `items=[]` 展示 `EmptyState`「当前无世界杯相关事件」+ 切回热门 Tab 操作，不呈现空白列表
- [x] 4.2 列表请求失败展示 `ErrorState` + 重试（重试 = `refetch`），不静默失败、不整页报错
- [x] 4.3 校验各空/错态文案经 i18n（含市场内容用 `{{eventName}}`/`{{optionName}}` 插值 key，不字符串拼接）

### 5. 只读、窄屏与验证（AC-7、AC-9、design D6）

- [x] 5.1 全流程只读走查：确认列表与输入流程无任何交易/下单/钱包连接入口
- [x] 5.2 窄屏适配：卡片/Tab/输入用 `min-width:0` + `overflow-wrap`/截断处理超长英文事件名/选项名；样式只用 `tokens.css` token，≤430px 无横向滚动、无文本溢出
- [x] 5.3 为关键组件补最小单测：卡片概览标签/不适用分支渲染、加载更多按 `has_more` 显隐、`local_cache` 回退标注、空/错态操作回调
- [x] 5.4 运行验证：`frontend/` 下 `pnpm typecheck` + `pnpm lint`（必要时 `pnpm test`）
