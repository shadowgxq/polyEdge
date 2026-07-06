## Context

前端全部页面（PRD §4.1/§4.2/§4.3/§4.4）都要消费「已算好的偏差结果」，但 `poly-data-integration`（归一化市场数据 + Redis 缓存 + 降级）与 `bias-algorithm`（纯计算偏差 + 三分类 + 排行分档）都不对外暴露 HTTP 接口（PRD §1.4、两 change 的 Non-Goals）。本 change 是二者之上的**后端对外 API 组合层**：把缓存读取到的 `MarketEvent` 喂给偏差计算，装配成统一 `ApiResponse[T]`，对外提供事件列表 / 单事件明细 / 事件输入 / 排行四类接口，并承接实时路径限流与上游不可用错误态映射。

技术基线：FastAPI + SQLAlchemy 2.0 同步 + Pydantic v2 + Redis，分层 `api → services → repositories → models`，`schemas`/`core` 横切（layer-definition.md）。对外契约与错误处理遵循 api-and-error-contract.md：统一 `ApiResponse[T]` / `success_response`，业务错误只抛 `BusinessException` 子类由全局 handler 转响应。

**本 change 不做**：Polymarket 拉取归一（`poly-data-integration`）、偏差公式（`bias-algorithm`）、前端页面（下游前端 change）、分享图片代理（`image-proxy`）。

## Goals / Non-Goals

**Goals:**

- 提供四类对外接口：默认列表（`hot` / `world_cup` 分类）、单事件明细、事件输入（slug 解析 + 名称搜索/本地模糊回退）、多事件排行（三榜）。
- 组合层只做编排：调用 `poly-data-integration` 的缓存读取方法 → `bias-algorithm` 的 `bias-scoring` 计算 → 装配对外 `schemas`，不重复实现数据访问或算法。
- 卡片级概览偏差标签口径：事件内 `|bias|` 最大选项的三分类标签 + 该选项名（PRD §4.1/AC-1）。
- 排行三榜与三分类阈值 `T` 对齐、互斥无交集，每项保留事件归属，TopN 截取在本层（bias-algorithm §5）。
- 实时路径（搜索 / slug 解析拉取 / 明细刷新）按 IP / 会话服务端限流（data-source §5）。
- 上游不可用与数据边界（不适用偏差 / 纯交易热度退化）转成明确响应态，不静默失败（PRD §5.2/§5.3）。

**Non-Goals:**

- 不拉取 Polymarket、不做字段归一、不做上游退避重试（属 `poly-data-integration`）。
- 不实现偏差公式、三分类阈值语义、排行分档口径（属 `bias-algorithm`，本层只调用并做 TopN 截取与响应装配）。
- 不实现任何前端页面、i18n 渲染（三分类标签 zh/en 两套由 `bias-algorithm` 产出，本层透传）。
- 不做分享图片代理（属 `image-proxy`）。
- 不新增 Postgres 表、无 Alembic 迁移。

## Decisions

**D1 — 路由按资源域分模块，统一 `/api/v1` 前缀。**
新增 `api/v1/events.py`（默认列表 / 单事件明细 / slug 解析 / 名称搜索）与 `api/v1/rankings.py`（三榜排行），在 `api/v1/__init__.py` 注册。路由只承担参数校验（`Query`/`Path`/`Body` 就近声明）、调用组合 service、`success_response` 返回，不写业务分支（api-and-error-contract.md）。备选（塞进单个 `analysis.py`）被否：资源域不清、不利 OpenAPI 分组。

**D2 — 组合编排落 `services`，依赖只向下。**
新增 `services/analysis_service.py`（或 `services/analysis/`）：编排 `MarketDataService`（`poly-data-integration`，缓存读取按 slug / 热门·世界杯默认列表）→ `bias-scoring` 计算函数（`bias-algorithm`，`services` 纯函数）→ 装配领域结果。组合层只依赖 `services`（`bias-scoring` 纯计算）与 `poly-data-integration` 暴露的数据读取 service，不直接触 `repositories` / Redis 数据访问（限流除外，见 D6）。理由：CLAUDE.md 依赖只向下、复用既有分层不新造平行结构。

**D3 — 数据 → 算法输入的适配集中一处。**
`MarketEvent` / `MarketOption`（`poly-data-integration` 的 `market-data-model` 契约）字段映射到 `bias-scoring` 输入契约（bias-algorithm §2 命名的选项级 `price/volume/liquidity/volume24hr/traders(可空)` + 事件级选项集合/commentCount）集中在组合层一个适配函数。字段名如不完全一致，仅在此适配层对齐，不改两侧口径（呼应 bias-algorithm design 风险项）。`has_participation` 谓词与退化判定复用 `market-data-model` / `bias-scoring`，本层不重判。

**D4 — 卡片级概览偏差标签：事件内 `|bias|` 最大选项。**
默认列表每个事件卡片调用 `bias-scoring` 得到各选项 `bias_i` 与标签后，取 `|bias_i|` 最大的选项，用其三分类标签作事件级概览结论并标注该选项名（PRD §4.1/AC-1）。事件「不适用偏差分析」（单选项 / `Σ price=0`，bias-algorithm §6）时卡片标注「不适用」而非硬造标签。并列最大时取 `bias_i` 绝对值相同者中的确定性优先项（如首个/较大 volume），在实现固化并单测，避免抖动。

**D5 — 排行 TopN 截取在 API 层，分档口径来自算法。**
`bias-algorithm` 的排行分档只给**全量**三档口径（泡沫 `bias_i≥+T` 降序 / 冷门 `bias_i≤−T` 升序 / 合理 `|bias_i|<T`，互斥无交集，bias-algorithm §5），TopN 截取属对外接口层（bias-algorithm §5 明确）。本层对当前 Tab 默认列表（`hot` / `world_cup`）读取各事件 → 逐事件算 `bias_i`（仍在其所属事件内归一）→ 汇总所有选项 → 调用算法分档 → 每榜按配置 `top_n` 截取，每项装配事件归属（slug/title/option/odds/bias/label）供回跳。某榜无入榜项返回空数组（前端空态，PRD §5.2），不整体报错。

**D6 — 实时路径限流：Redis 计数 + 业务异常，fail-open。**
对绕过预取缓存的实时请求（名称搜索、slug 解析拉取、单事件明细刷新）按 IP / 会话在 Redis 滑动/固定窗口计数，超阈值抛 `BusinessException` 子类（如 `RateLimitExceededException`，HTTP 429），由全局 handler 转 `ApiResponse` 错误态。限流 Redis 能力放 `services`（如 `services/rate_limit_service.py`），经 `core/redis_client` 的 `@redis_safe` 封装，计数失败 `default=0`（fail-open，不误伤，呼应 infrastructure.md 限流降级方向）。默认列表 / 排行走预取缓存，通常不限流或用更宽松阈值。窗口/阈值经 `Settings` 配置。备选（网关层限流）被否：本期无网关、按 IP/会话的应用内限流最贴 data-source §5。

**D7 — 上游不可用与数据边界的错误态映射。**
`poly-data-integration` 拉取失败且无缓存时抛 `UpstreamUnavailableException`（该异常由 `poly-data-integration` 定义于 `core/exceptions`；若其尚未落地，本 change 在 `core/exceptions` 补 `BusinessException` 子类并分配业务 code，集成时以上游定义为准，不重复定义）。本层不吞该异常，交全局 handler 转 `ApiResponse` 错误态（PRD §5.2/§5.3）。数据边界（事件「不适用偏差分析」、选项被排除、全事件退化为纯交易热度）不是错误，而是**成功响应内的标注字段**（`applicability` / `degraded_trade_only` / 选项 `excluded`），前端据此展示（PRD §5.2、bias-algorithm §6）。回退缓存快照的陈旧数据一律带 `data_snapshot_at`，前端提示「数据可能非最新」，本层只透传不混淆。

**D8 — 事件输入拆两个接口：slug 解析 + 名称搜索。**
链接/slug 走 `POST /api/v1/events/resolve`（后端从链接提取 slug、判定有效性、按 slug 拉取，PRD §4.2 链接解析归属在后端）；名称走 `GET /api/v1/events/search`（Polymarket 搜索），搜索能力不可用时退化为在已缓存事件集本地模糊匹配，响应带 `search_scope`（`upstream` / `local_cache`）供前端标注「仅在当前收录事件范围内搜索」（PRD §4.2、data-source §3）。解析不出 / 搜不到返回明确空态（`resolve` 抛业务「未找到」错误态或空 data；`search` 返回空候选列表 + scope），不静默失败（PRD §5.2）。

**D9 — 快照时间一致性透传。**
默认列表（长 TTL）与单事件明细价格（短 TTL）各带自己的 `data_snapshot_at`（`market-data-cache` 分层 TTL 使二者可能有时间差，data-source §4）。本层原样透传各自快照时间，不合并、不谎称同刻，由前端按 data-source §4「以明细页更短 TTL 价格为准」展示。

## Risks / Trade-offs

- [上游 `poly-data-integration` / `bias-algorithm` 契约尚在并行开发，字段名/方法签名可能微调] → 组合层集中适配（D3）+ 依赖二者已冻结的 spec 契约；集成期只在适配层对齐，不改本层对外 schema。
- [`UpstreamUnavailableException` 归属上游定义，若上游未先落地会缺失] → D7 约定：缺失时本 change 临时补于 `core/exceptions` 并分配 code，集成以上游为准，避免双定义漂移（集成时删本地临时定义）。
- [默认列表/排行需对多事件逐个算 bias，计算量随事件数放大] → 数据走预取缓存（`poly-data-integration`）、`bias-scoring` 为无 IO 纯函数、结果可随缓存快照复用；TopN 与 page_size 上限约束返回规模（PRD §4.1/§4.4 规模上限）。
- [实时限流按 IP 易误伤 NAT 后多用户 / 被伪造 IP 绕过] → 阈值取自配置可调、fail-open 不阻断可用性；会话维度补充；本期只需满足 data-source §5「避免放大上游压力」，非安全级防护。
- [卡片概览标签取 `|bias|` 最大在并列时不确定] → D4 固化确定性 tie-break 并单测，防前端展示抖动。

## Migration Plan

- 无 DB 迁移（无表变更）。新增限流窗口/阈值、排行 `top_n`、`page_size` 上限等配置写入 `.env.example`。
- 部署：随后端发布；路由在 `api/v1` 注册即可达。回滚即移除路由与组合 service 模块、配置项，无 schema 变更、无数据回滚负担。
- 集成顺序：依赖 `poly-data-integration` 与 `bias-algorithm` 先落地；本 change 的组合 service 对二者的 service/函数做集成对接。

## Open Questions

- Polymarket 是否提供可用的公开名称搜索能力，决定 `GET /events/search` 主路径还是直接走本地模糊回退——由 `poly-data-integration` 技术方案 API 探针固化（data-source §3 已标注待验证）；本层按「搜索不可用则本地模糊 + `search_scope` 标注」双路径预留，不阻塞。
- 实时限流的窗口粒度（固定窗口 vs 滑动窗口）与默认阈值具体数值，在实现阶段按上游限流约束与体验权衡固化（配置可调）。
- 会话维度的标识来源（本期无登录，PRD §1.3）：以匿名会话标识（如前端生成的 session id / cookie）还是仅 IP，实现阶段确定；缺会话标识时退化为纯 IP 维度。
