## Context

偏差分析全链路依赖一份口径一致、带快照时间、可缓存、可降级的 Polymarket 归一化市场数据。上游只有 Gamma（元数据）+ CLOB（价格）双 API，有速率与稳定性约束（PRD §1.4、data-source §1/§5）。本 change 是后端数据底座，向 `bias-algorithm`（消费选项级量与参与谓词）与 `analysis-api`（消费缓存读取与快照时间）提供契约，**本 change 不实现偏差公式、不暴露对外 HTTP 接口、不做图片代理**。

技术基线：FastAPI + SQLAlchemy 2.0 同步 + Pydantic v2 + Redis，分层 `api → services → repositories → models`，`schemas`/`core` 横切（见 layer-definition.md）。归一化数据只落 Redis，不落 Postgres。

## Goals / Non-Goals

**Goals:**

- 用 Polymarket 客户端拉取 Gamma + CLOB 并归一到内部事件/选项模型，字段口径对齐 data-source §2 与 bias-algorithm §2。
- Redis 分层 TTL 缓存 + 定时预取默认列表，用户请求优先命中缓存。
- 上游指数退避重试；拉取失败优先回退缓存快照并标注快照时间，无缓存返回错误态。
- 提供「无 per-option 参与数据」判定谓词（缺失/null 为无、0 为有效 0）。

**Non-Goals:**

- 不实现偏差评分/三分类（属 `bias-algorithm`；本 change 只产出其输入量）。
- 不暴露对外 REST 接口（属 `analysis-api`）、不做图片代理（属 `image-proxy`）。
- 不做时间序列/历史存储；只保存当前快照。
- 不新增 Postgres 表、无 Alembic 迁移。

## Decisions

**D1 — 数据模型用 Pydantic 领域模型，缓存到 Redis，不建 ORM 表。**
归一化事件/选项是只读快照、TTL 短、无需关系查询/事务，data-source §4 明确缓存位置在 Redis。故 `market-data-model` 落在 `schemas`（Pydantic v2 契约：`MarketEvent` / `MarketOption`，字段 `price / volume / liquidity / volume24hr / traders(可空) / comment_count(事件级) / data_snapshot_at / price_source / degraded_note`）。备选（建 Postgres 表持久化）被否：徒增迁移与写放大，与「快照 + Redis」口径不符。

**D2 — 价格主源 CLOB midpoint，回退 Gamma outcomePrices，模型标注价源。**
锚定 data-source §2 与 bias-algorithm §3.1：主取 CLOB midpoint / best bid-ask，不可得时回退 `outcomePrices`，`price_source` 字段记录实际来源，供下游与前端标注口径限制。

**D3 — 二元 vs 多 outcome 粒度按缺失兜底，不臆造选项级值。**
锚定 data-source §2：二元市场字段直接作选项级；多 outcome 且 `volume/liquidity/volume24hr` 仅 market 级、无法拆到 outcome 时，该分量置缺失并标注，交由 `bias-algorithm` §3.2 的除零/缺失兜底处理。本 change 只负责「诚实地标缺失」，不做平均/估算。

**D4 — 参与数据谓词固化为 `has_participation(option)`。**
锚定 PRD §5.2、bias-algorithm §3.5：`traders`/`holders` 缺失或 `null` → 无（`False`）；值为 `0` → 有效 0（`True`）。谓词放在 `market-data-model` 契约旁（纯函数/模型方法），使 `bias-algorithm` 的全事件退化判定与本 change 同一事实源。

**D5 — 分层缓存键与 TTL。**
锚定 data-source §4：元数据/列表用较长 TTL（分钟级）、价格/赔率用较短 TTL（秒~十秒级），分别独立 key，具体数值经 `core/config.Settings` 从 `.env` 读取（`METADATA_TTL` / `PRICE_TTL` 等）。缓存访问封装为 repository（经 `core/redis_client`，不直连 Redis）。快照时间随缓存值一同写入并回读。

**D6 — 客户端与缓存分层归属。**
`PolymarketClient`（Gamma + CLOB HTTP，用 `httpx` 同步 Client，退避重试）+ `MarketDataCacheRepository`（Redis 读写）归 `repositories` 层（对外部数据源与缓存的数据访问）；归一映射、降级编排、预取业务放 `services`（`MarketDataService`）。降级/退避编排是业务规则，只在 service。分层：`services → repositories`，不反向。

**D7 — 定时预取用轻量调度，受限流约束。**
默认列表（热门 + 世界杯子集）由后端定时任务预取入缓存（data-source §3/§4）。调度器（APScheduler 或应用内 lifespan 定时协程/线程）在应用启动挂载，频率与单次批量上限经配置，避免放大上游压力。预取失败按 D8 降级、记录日志、不中断进程。

**D8 — 退避重试 + 缓存回退降级链。**
锚定 PRD §5.2/§5.3、data-source §5：上游 429/瞬时错误 → 指数退避重试至上限 → 仍失败则 service 优先回退（即使过期的）缓存快照并带其 `data_snapshot_at`；无缓存则抛 `BusinessException` 子类（如 `UpstreamUnavailableException`），由 `analysis-api` 的全局 handler 转 `ApiResponse` 错误态。不静默返回空成功。

**D9 — 可测性：Mock/故障注入开关。**
锚定 PRD §1.4：非生产可注入「拉取失败 ± 缓存命中」「参与数据缺失退化」分支。用配置开关 + 可替换的 client 实现（测试用 FakeRedis + stub client），Mock 不进生产数据路径（data-source §4）。

## Risks / Trade-offs

- **上游字段真实可得性未探针验证（traders/holders、多 outcome 粒度、CLOB midpoint）** → 归一层用「诚实标缺失 + `price_source`/`degraded_note` 标注」吸收不确定性；字段映射集中在一处便于探针后固化（data-source §2 注）。
- **过期缓存回退可能展示陈旧数据** → 回退结果一律带 `data_snapshot_at`，由前端提示「数据可能非最新」，满足 PRD §5.3 快照标注；不混淆为最新。
- **分层 TTL 导致列表快照与明细价格时间差** → 契约层保留各自 `data_snapshot_at`，一致性口径（以更短 TTL 价格为准）由 `analysis-api`/前端承接（data-source §4 快照一致性），本 change 只保证字段可用。
- **定时预取叠加实时请求可能触发上游限流** → 预取频率/批量上限 + 退避重试双重约束；实时限流（IP/会话）属 `analysis-api`，本 change 只对上游退避。
- **新增依赖（httpx / 调度库）** → 评估必要性后入 `pyproject.toml` 并 `uv lock`，同步 IO 用 httpx 同步 Client 契合模板「不写 async」。

## Migration Plan

- 无 DB 迁移（Redis-only）。新增配置项写入 `.env.example`。
- 部署：随后端发布；调度器在应用 lifespan 启动挂载，回滚即移除模块与配置，无 schema 变更、无数据回滚负担。

## Open Questions

- Polymarket 公开 API 的确切 endpoint / 分页参数 / 世界杯筛选标签取值 —— 待技术方案 API 探针验证后在映射层固化（data-source §2/§3 已标注为待验证）。
- `traders`/`holders` 是否逐事件可得、多 outcome 是否需 CLOB 逐选项深度补齐 —— 探针后决定，接口按缺失兜底预留。
