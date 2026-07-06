# Tasks

> 本 change 为**前端单端**：只填充 `web-app-shell-i18n` 预留的 `/ranking` outlet，消费其路由/回跳/基元与 `analysis-api` 排行接口。只保留 `## 前端` 分节。**不写后端**——排行聚合/分档/排序/TopN 由 `analysis-api` + `bias-algorithm §5` 提供。
>
> 消费的后端接口（由 `analysis-api` 提供，本 change 不实现）：
> `GET /api/v1/rankings`｜query：`category`（`hot`|`world_cup`，默认 `hot`）、`top_n`（默认取后端配置，前端不传）｜出参 `data`：`RankingBoards`={ category, bubble:`RankingItem`[], underhyped:`RankingItem`[], fair:`RankingItem`[] }；`RankingItem`={ event_slug, event_title, option_name, price, bias_score, label:{ zh, en } }；空榜为 `[]`。
>
> 首次编辑前端前先读 `docs/frontend/standards/frontend-development.md`、`components/components.md`、`components/component-splitting.md`、`standards/file-organization.md`。

## 前端

- [x] 1.1 建 `pages/ranking/` 模块目录，规划 `RankingPage.tsx` + `components/` + `ranking.api.ts` / `ranking.queries.ts` / `ranking.types.ts` 结构（遵循 file-organization / component-splitting，design D1）
- [x] 1.2 在 `ranking.types.ts` 定义 `RankingCategory`（`'hot'|'world_cup'`）、`RankingBoards`、`RankingItem` 类型，字段名对齐后端 snake_case 契约（`event_slug`/`event_title`/`option_name`/`price`/`bias_score`/`label`）；**依赖后端接口 `GET /api/v1/rankings`**
- [x] 1.3 在 `ranking.api.ts` 实现 `fetchRankings({ category })`：经 `shared/api` `requestClient` 调 `GET /api/v1/rankings`，解包 `ApiResponse.data` 返回 `RankingBoards`；`top_n` 不传用后端默认（design D3）；**依赖后端接口 `GET /api/v1/rankings`**
- [x] 1.4 在 `ranking.queries.ts` 实现 `useRankingsQuery(category)`：queryKey `['rankings', category]`，沿用外壳 `QueryClient` 默认项，服务端态经 Query 承载（design D3）
- [x] 1.5 实现 `RankingItemRow` 组件：展示事件标题、选项名、赔率（隐含概率）、偏差评分、`BiasLabel`；按榜别映射 `category`（`bubble→hot`/`underhyped→cold`/`fair→fair`）注入基元；整行为回跳 `/events/:eventId`（`event_slug` 作参数）入口，键盘可达 + i18n 插值 `aria-label`（design D2/D7）
- [x] 1.6 实现 `RankingBoard` 组件：单榜标题 + 榜单项列表；该榜为空数组时渲染 `EmptyState`（本地化空态文案），其余情况按后端顺序渲染 `RankingItemRow`（design D6）
- [x] 1.7 实现 `RankingBoards` 容器组件：宽屏三榜并列分区、≤430px 窄屏三榜分段 Tab（bubble/underhyped/fair 三段，激活段为本地 UI 态）+ 卡片纵向排列；`min-width:0`/`overflow-wrap` + 超长文本截断/换行防溢出，布局仅用 `tokens.css` token（design D5，AC-9）
- [x] 1.8 实现 `RankingPage.tsx`（route page，只做 composition）：读取当前分类（复用外壳/列表既有分类来源，缺失时 `hot` 默认并预留 `category` 注入点，design D4）→ `useRankingsQuery` → 按 `isPending`/`isError`/success 编排：加载态占位、`ErrorState` + `refetch` 重试、success 渲染 `RankingBoards`（design D6）
- [x] 1.9 将 `RankingPage` 挂到外壳 `/ranking` 路由，替换占位 outlet 组件
- [x] 1.10 补 i18n：在 `shared/i18n/resources/{en,zh}.json` 增排行相关 key（三榜标题、各榜空态说明、加载/错误/重试文案、榜单项 `aria-label` 插值 key），含事件/选项内容的句子用插值不拼接（PRD §4.6）；`BiasLabel` 复用既有 `bias.label.*` 文案
- [x] 1.11 校验只读无交易入口（AC-7）：榜单项只提供回跳明细入口，无交易/下单/钱包元素
- [x] 1.12 验证：`frontend/` 下 `pnpm typecheck` + `pnpm lint`（必要时 `pnpm test`）
