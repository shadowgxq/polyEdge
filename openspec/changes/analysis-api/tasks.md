# Tasks

> 本 change 为**后端对外 API 层**（组合数据 + 算法），只保留 `## 后端` 分节。无 Postgres 表变更、无 Alembic 迁移。**不写任何前端页**——前端消费由下游 `event-list-and-input` / `single-event-detail` / `bias-ranking` change 承接。下方「提供的接口」小节给出对外契约（路径 + 出入参）供其消费。
> 依赖：`poly-data-integration`（`MarketDataService` 缓存读取、`market-data-model` 契约、`UpstreamUnavailableException`）与 `bias-algorithm`（`bias-scoring` 计算与排行分档口径）。契约复用二者 artifacts，不自拟。

## 后端

### 1. 配置与依赖

- [ ] 1.1 在 `core/config.Settings` 增配置项：默认列表每页上限（`event_list_page_size`）、排行默认 TopN（`ranking_top_n`）、实时路径限流窗口/阈值（`realtime_rate_limit_window` / `realtime_rate_limit_max`）；同步补 `.env.example`（无敏感值，均给合理默认）
- [ ] 1.2 确认 `UpstreamUnavailableException` 由 `poly-data-integration` 在 `core/exceptions` 定义；若上游尚未落地，在 `core/exceptions` 临时补 `BusinessException` 子类并分配业务 code，集成时以上游定义为准（避免双定义漂移，design D7）

### 2. 对外响应 schemas（schemas/analysis.py）

- [ ] 2.1 定义选项分析出参 `OptionAnalysis`（选项名、赔率/隐含概率、热度、`bias_score`、三分类标签 zh/en、`excluded` 标注），锚定 bias-algorithm §3/§4 与 api-and-error-contract.md（snake_case Pydantic 出参）
- [ ] 2.2 定义单事件明细出参 `EventDetail`（slug/title、`options: list[OptionAnalysis]`、事件级 `comment_count`、`applicability`（是否适用偏差）、`degraded_trade_only`、`data_snapshot_at`）
- [ ] 2.3 定义事件卡片出参 `EventCard`（slug/title、选项赔率概览、事件级概览偏差标签 + 标注选项名 / 或「不适用」标注、`data_snapshot_at`）与列表出参（`items` + 分类 + 空态标识）
- [ ] 2.4 定义排行出参 `RankingBoards`（`bubble` / `underhyped` / `fair` 三榜，每项 `RankingItem`：事件 slug/title、选项名、赔率、`bias_score`、标签）
- [ ] 2.5 定义搜索候选出参 `EventSearchResult`（`candidates` + `search_scope: upstream|local_cache`）；全部出参一律经 `ApiResponse[T]` 返回，不手拼 dict

### 3. 组合编排 service（services/analysis_service.py）

- [ ] 3.1 实现 `MarketEvent`/`MarketOption`（`market-data-model`）→ `bias-scoring` 输入契约的适配函数（集中一处，字段名不一致仅在此对齐，不改两侧口径，design D3）
- [ ] 3.2 实现单事件分析编排：`MarketDataService` 按 slug 读取 → 适配 → `bias-scoring` 计算 → 装配 `EventDetail`（含退化/排除/不适用标注、commentCount、快照时间），依赖只向下 `services → (poly service / bias 纯函数)`（design D2/D7）
- [ ] 3.3 实现默认列表编排：按分类（`hot`/`world_cup`）读取默认列表 → 逐事件算偏差 → 取事件内 `|bias_i|` 最大选项标签作卡片概览标签并标注选项名（不适用事件标注「不适用」），受 `event_list_page_size` 约束，并列最大时用确定性 tie-break（design D4）
- [ ] 3.4 实现排行编排：按分类读取默认列表所有事件 → 逐事件算 `bias_i` → 汇总所有选项 → 调用 `bias-algorithm` 排行分档（泡沫≥+T 降序 / 冷门≤−T 升序 / 合理 |bias|<T，互斥无交集）→ 每榜按 `ranking_top_n` 截取、每项装配事件归属（design D5、bias-algorithm §5）
- [ ] 3.5 实现事件输入编排：`resolve`（从链接/slug 提取 slug → 判定有效性 → 按 slug 拉取；解析不出抛「未找到」业务错误态）与 `search`（Polymarket 搜索，不可用则已缓存事件集本地模糊匹配并标 `search_scope`，搜不到返回空候选带 scope）（design D8、data-source §3）
- [ ] 3.6 数据边界作为成功响应内标注、上游 `UpstreamUnavailableException` 不吞由全局 handler 转错误态、回退缓存快照透传其 `data_snapshot_at`（design D7/D9、PRD §5.2/§5.3）

### 4. 实时路径限流（services/rate_limit_service.py）

- [ ] 4.1 实现按 IP / 会话的 Redis 窗口计数限流能力（经 `core/redis_client` 的 `@redis_safe`，计数故障 `default=0` fail-open），超阈值抛 `RateLimitExceededException`（HTTP 429，补入 `core/exceptions` 并分配业务 code）（design D6、infrastructure.md、data-source §5）
- [ ] 4.2 在实时路径（`search` / `resolve` 拉取 / 明细刷新）接入限流依赖；默认列表/排行走预取缓存不接入或用更宽松阈值

### 5. 路由（api/v1）

- [ ] 5.1 新建 `api/v1/events.py`：默认列表、单事件明细、slug 解析、名称搜索四个端点，参数就近声明（`Query`/`Path`/`Body`），调用组合 service、`success_response` 返回，标 `response_model=ApiResponse[T]` 与 `tags`
- [ ] 5.2 新建 `api/v1/rankings.py`：排行端点，同上规范
- [ ] 5.3 在 `api/v1/__init__.py`（或 `main.py`）注册两路由，确认 `/api/v1` 前缀下实际可达、`/docs` 可见

### 6. 提供的接口（路径 + 出入参，供下游前端 change 消费）

> 下列为本 change 对外契约，前端 change 依赖这些接口，本 change 不实现前端页。响应一律为 `ApiResponse[T]` 信封（`{ code, message, data }`）。

- [ ] 6.1 `GET /api/v1/events`｜入参 query：`category`（`hot`|`world_cup`，默认 `hot`）、`page`（默认 1）、`page_size`（默认取配置上限，`ge=1,le=上限`）｜出参 `data`：`{ category, items: EventCard[], has_more }`；`EventCard`={ slug, title, options:[{name, price}], overview_label:{ zh, en } | null, overview_option_name | null, applicable: bool, data_snapshot_at }。供 `event-list-and-input` 消费
- [ ] 6.2 `GET /api/v1/events/{slug}`｜入参 path：`slug`｜出参 `data`：`EventDetail`={ slug, title, comment_count, applicable: bool, degraded_trade_only: bool, data_snapshot_at, options:[`OptionAnalysis`] }；`OptionAnalysis`={ name, price, heat, bias_score, label:{ zh, en } | null, excluded: bool }。实时刷新路径受限流。供 `single-event-detail` 消费
- [ ] 6.3 `POST /api/v1/events/resolve`｜入参 body：`{ input: str }`（Polymarket 事件链接或 slug）｜出参 `data`：`EventDetail`（同 6.2）；解析不出返回「未找到」错误态（非 code=0）。实时路径受限流。供 `event-list-and-input` 消费
- [ ] 6.4 `GET /api/v1/events/search`｜入参 query：`q`（事件名称）、`limit`（默认合理值）｜出参 `data`：`{ candidates:[{ slug, title }], search_scope: "upstream"|"local_cache" }`；搜不到 `candidates` 为空数组并带 scope。实时路径受限流。供 `event-list-and-input` 消费
- [ ] 6.5 `GET /api/v1/rankings`｜入参 query：`category`（`hot`|`world_cup`，默认 `hot`）、`top_n`（默认取配置）｜出参 `data`：`RankingBoards`={ category, bubble:[`RankingItem`], underhyped:[`RankingItem`], fair:[`RankingItem`] }；`RankingItem`={ event_slug, event_title, option_name, price, bias_score, label:{ zh, en } }；空榜为 `[]`。供 `bias-ranking` 消费

### 7. 验证

- [ ] 7.1 补单元/集成测试（`tests/conftest.py` 内存 SQLite + FakeRedis + stub 上游 service）：默认列表分类与概览标签、单事件明细退化/排除/不适用标注、slug 解析成功/未找到、搜索上游/本地回退/空候选、排行三榜互斥无交集 + TopN + 空榜、上游不可用转错误态、实时限流超阈值 429 与 fail-open
- [ ] 7.2 跑 `make lint`（ruff）+ `make test`（pytest）通过；确认无 Postgres 表变更故不需 `make migrate`/`make upgrade`
