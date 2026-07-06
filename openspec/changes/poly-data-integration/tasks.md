# Tasks

> 本 change 为后端单端，只含 `## 后端` 分节（openspec/config.yaml）。归一化数据仅落 Redis，**无 Postgres 表变更、无 Alembic 迁移**（见 design.md D1）。不对外暴露 HTTP 接口（属 analysis-api）。

## 后端

### 1. 依赖与配置

- [ ] 1.1 评估并新增第三方依赖（HTTP 客户端 `httpx` 同步 Client、定时调度库），写入 `pyproject.toml` 并 `uv lock`（不在代码里临时安装）
- [ ] 1.2 在 `core/config.Settings` 增配置项：Polymarket Gamma/CLOB base URL、分层 TTL（`metadata_ttl`/`price_ttl`）、预取频率与单次批量上限、退避参数（基础间隔/最大重试/上限）、世界杯筛选标签/关键词、Mock/故障注入开关；同步补 `.env.example`（密钥类不硬编码、不入库、不进 Git）

### 2. 归一化数据模型契约 (market-data-model)

- [ ] 2.1 在 `schemas` 定义 Pydantic v2 契约 `MarketOption`（`price / volume / liquidity / volume24hr / traders(可空) / price_source / degraded_note`）与 `MarketEvent`（`slug / title / options / comment_count(事件级) / data_snapshot_at / category`），字段口径对齐 data-source §2、bias-algorithm §2
- [ ] 2.2 实现「无 per-option 参与数据」判定谓词 `has_participation(option)`：`traders` 缺失或 `null` → False（无）、值为 `0` → True（有效 0），锚定 PRD §5.2、bias-algorithm §3.5，并附单元测试覆盖 缺失/null/0 三态
- [ ] 2.3 固化价源标注枚举与 `data_snapshot_at` 语义（快照获取时刻），供下游与缓存复用（data-source §4、PRD §5.3）

### 3. Polymarket 客户端 (polymarket-client)

- [ ] 3.1 在 `repositories` 实现 `PolymarketClient`（`httpx` 同步）：按 slug 从 Gamma 拉事件/市场元数据、从 CLOB 拉选项价格；仅只读请求，不触达任何交易 endpoint（PRD §1.3、data-source §5）
- [ ] 3.2 实现字段归一映射到 `market-data-model`：价格主取 CLOB midpoint、不可得回退 Gamma `outcomePrices` 并写 `price_source`（data-source §2、bias-algorithm §3.1）
- [ ] 3.3 实现二元 vs 多 outcome 粒度处理：二元直接取选项级；多 outcome 且成交量/流动性仅 market 级、无法拆到选项时该分量置缺失并写 `degraded_note`，不臆造/估算（data-source §2）
- [ ] 3.4 实现默认热门列表拉取（按成交量/流动性等排序、受批量上限约束）与世界杯子集筛选（按标签/关键词过滤同一数据源）（PRD §4.1、data-source §1/§3）
- [ ] 3.5 实现上游指数退避重试：对 429/瞬时错误按配置退避重试至上限，耗尽后抛上游失败异常，不静默返回空（PRD §5.2、data-source §5）

### 4. Redis 分层缓存 (market-data-cache)

- [ ] 4.1 在 `repositories` 实现 `MarketDataCacheRepository`（经 `core/redis_client`，不直连 Redis）：元数据/列表与价格/赔率分层 key + 分层 TTL 读写，缓存值随带 `data_snapshot_at`（data-source §4、PRD §5.3）
- [ ] 4.2 实现命中缓存直接返回（未过期不打上游）与过期/未命中回源标识

### 5. 业务编排 (services)

- [ ] 5.1 实现 `MarketDataService`：编排 client 拉取 → 归一 → 写缓存 → 返回带快照时间的领域值；降级/退避编排只在 service（依赖只向下 `services → repositories`）
- [ ] 5.2 实现拉取失败降级链：退避耗尽后优先回退（含过期）缓存快照并带其 `data_snapshot_at`；无缓存抛 `BusinessException` 子类（如 `UpstreamUnavailableException`，供 analysis-api 全局 handler 转 `ApiResponse` 错误态），不静默失败（PRD §5.2/§5.3、data-source §4/§5）
- [ ] 5.3 提供供下游 `analysis-api` 消费的缓存读取/回源方法（按 slug 取单事件、取热门/世界杯默认列表），返回统一带快照时间的 `MarketEvent`（本 change 不建路由）

### 6. 定时预取与可测性

- [ ] 6.1 挂载后端定时预取任务（应用 lifespan 启动）：按配置频率对热门 + 世界杯默认列表批量预取入缓存，受批量上限/退避约束；预取失败记录日志、走降级、不中断进程（PRD §4.1、data-source §3/§4）
- [ ] 6.2 实现 Mock/故障注入开关（非生产）：可稳定复现「拉取失败 ± 缓存命中」「参与数据缺失退化」分支，Mock 不进生产数据路径（PRD §1.4、data-source §4）

### 7. 验证

- [ ] 7.1 补单元/集成测试（`tests/conftest.py` 的内存 SQLite + FakeRedis + stub client）：归一映射、价源回退、粒度缺失兜底、参与谓词三态、分层 TTL、退避重试、失败回退缓存/无缓存报错、预取入缓存
- [ ] 7.2 跑 `make lint`（ruff）+ `make test`（pytest）通过；确认无 Postgres 表变更故不需 `make migrate`/`make upgrade`
