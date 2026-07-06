## Why

偏差分析全链路（bias-algorithm 计算、analysis-api 对外接口）都依赖一份口径一致、带快照时间、可缓存、可降级的 Polymarket 归一化市场数据；而 Polymarket 只提供 Gamma + CLOB 双 API，有速率与稳定性约束（PRD §1.4、data-source §1/§5）。本 change 建立后端数据接入底座：把 Gamma + CLOB 的原始字段归一到内部事件/选项模型，经 Redis 分层 TTL 缓存与定时预取对上游降压，并在上游失败时优先回退缓存快照，为下游 change 提供稳定契约。

## What Changes

- 新增 Polymarket 客户端，对接 Gamma API（事件/市场/成交量/流动性/24h 成交量/评论数元数据）与 CLOB API（选项价格/隐含概率），只读拉取（data-source §1/§5、bias-algorithm §2）。
- 定义内部**归一化事件/选项数据模型**（跨 change 共享契约）：把 Polymarket 侧字段映射到 `price_i / volume_i / liquidity_i / volume24hr_i / traders_i / commentCount` 口径，价格主取 CLOB midpoint、`outcomePrices` 为退化回退，并区分二元市场与多 outcome market 的挂载粒度（data-source §2、bias-algorithm §2/§3.1）。
- 定义「无 per-option 参与数据」判定谓词：字段缺失或 `null` 视为无（供下游触发退化），值为 `0` 视为有效 0（PRD §5.2、data-source §2、bias-algorithm §3.5）。
- 新增 Redis 分层 TTL 缓存：元数据/列表 TTL 较长（分钟级）、价格/赔率 TTL 较短（秒~十秒级），缓存对象一律带**数据快照时间**（data-source §4、PRD §5.3）。
- 新增后端定时预取任务：对默认列表（Polymarket 热门 + 世界杯筛选子集）批量预取入缓存，受上游限流约束控制频率与单次批量上限（data-source §3/§4）。
- 新增上游访问韧性：对 Polymarket 双 API 采用**指数退避重试**；拉取失败优先回退缓存快照并标注快照时间，无缓存返回错误态，不静默失败（PRD §5.2/§5.3、data-source §5）。

## Capabilities

### New Capabilities

- `market-data-model`: 跨 change 共享的内部归一化事件/选项数据契约——字段口径映射（价格主源/回退、成交量/流动性/24h/参与人数/评论数）、数据快照时间、二元 vs 多 outcome 粒度处理、无 per-option 参与数据判定谓词。供 `bias-algorithm` 与 `analysis-api` 复用。
- `polymarket-client`: 对接 Polymarket Gamma + CLOB 双 API 的只读拉取与归一化——按 slug/热门规则/世界杯筛选拉取事件与选项、映射到 `market-data-model`、上游指数退避重试。
- `market-data-cache`: Redis 分层 TTL 缓存、默认列表定时预取、快照时间标注、拉取失败回退缓存快照 / 无缓存报错的降级编排。

### Modified Capabilities

<!-- 无：openspec/specs/ 目前为空，本 change 全部为新增能力。 -->

## Impact

- 后端新增：Polymarket 客户端模块（Gamma + CLOB HTTP 访问）、归一化数据模型（Pydantic 领域模型 / schemas）、Redis 缓存仓储、定时预取调度、退避重试工具。
- 依赖分层：`api → services → repositories → models`；本 change 主要落在 `services`（拉取归一 + 降级编排）、`repositories`（Redis 缓存访问、Polymarket 客户端封装）、`schemas/models`（归一化契约）。本 change **不对外暴露 HTTP 接口**（属 `analysis-api`）。
- 配置：Polymarket API base URL、分层 TTL、预取频率/批量上限、退避参数、世界杯筛选标签经 `core/config.Settings` 从 `.env` 读取，不硬编码。
- 数据存储：归一化数据仅缓存在 Redis（JSON 快照），**不新增 Postgres 表**，因此本 change 无 Alembic 迁移。
- 新增第三方依赖：HTTP 客户端（如 `httpx`）与调度（如 APScheduler 或等价定时机制），入 `pyproject.toml` 并 `uv lock`。
- 下游契约假设：`bias-algorithm` 消费 `market-data-model` 的选项级量与参与数据谓词；`analysis-api` 消费缓存读取接口与快照时间。
