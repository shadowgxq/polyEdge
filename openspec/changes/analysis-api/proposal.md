## Why

前端各页面（事件列表、单事件明细、事件输入、多事件排行）需要「已算好的偏差结果」，但当前仓库只有数据底座（`poly-data-integration`）与纯计算模块（`bias-algorithm`），二者都不对外暴露 HTTP 接口（PRD §1.4）。本 change 建立**后端对外 API 层**：组合归一化市场数据与偏差算法，产出统一 `ApiResponse[T]` 结果，并对绕过预取缓存的实时路径施加服务端限流、把上游不可用转成明确业务错误态，作为所有前端页 change 的接口事实源。

## What Changes

- 新增**默认事件列表接口**：按 `hot`（Polymarket 热门）与 `world_cup`（世界杯筛选子集）两个分类返回事件卡片，卡片含选项/赔率与**事件级概览偏差标签**（取事件内 `|bias|` 最大选项的三分类标签并标注该选项名），带数据快照时间（PRD §4.1/AC-1、bias-algorithm §4）。
- 新增**单事件明细接口**：按 slug 返回每个可分析选项的赔率（隐含概率）/热度/偏差评分/三分类标签与降级标注（纯交易热度 / 不适用偏差分析），事件级 `commentCount` 与数据快照时间（PRD §4.3/§5.2、bias-algorithm §3.5/§6）。
- 新增**事件输入接口**：链接/slug 解析（后端提取 slug 并判定有效性）→ 按 slug 拉取；名称搜索走 Polymarket 搜索，搜索不可用时退化为在**已缓存事件集**本地模糊匹配并标注搜索范围（PRD §4.2/AC-2、data-source §3）。
- 新增**多事件排行接口**：对当前 Tab 默认列表（`hot` / `world_cup`）聚合所有选项，输出泡沫风险榜（降序）/冷门机会榜（升序）/合理列表三榜，每项保留事件归属可回跳，按配置 `top_n` 截取（PRD §4.4/AC-4、bias-algorithm §5）。
- 新增**响应契约 schemas**：事件卡片 / 单事件明细 / 选项分析 / 榜单项 / 搜索候选，全部为 Pydantic v2 出参模型（snake_case），一律经 `ApiResponse[T]` / `success_response(...)` 返回。
- 新增**实时路径服务端限流**：对手动搜索、按 slug 解析拉取、单事件明细刷新等绕过预取缓存的实时请求按 IP / 会话限流（经 Redis），触发上限抛业务错误（data-source §5）。
- 新增**上游不可用错误态映射**：把 `poly-data-integration` 抛出的 `UpstreamUnavailableException`（及数据缺失/不适用边界）经全局 handler 转成 `ApiResponse` 错误态，不静默失败、不返回空成功（PRD §5.2/§5.3、data-source §4/§5）。

## Capabilities

### New Capabilities

- `analysis-event-api`: 对外事件类 HTTP 接口——默认列表（`hot` / `world_cup` 分类，卡片级概览偏差标签）、单事件明细（选项级赔率/热度/偏差/三分类/降级标注 + 事件级 commentCount + 快照时间）、事件输入（slug 解析 + 名称搜索/缓存集本地模糊回退）。组合数据 service → 偏差算法 → 装配响应 schema。
- `analysis-ranking-api`: 对外排行 HTTP 接口——对当前 Tab 默认列表聚合出泡沫/冷门/合理三榜，与三分类阈值 `T` 对齐互斥无交集，每项保留事件归属、按配置 TopN 截取。
- `analysis-api-runtime`: API 层横切能力——统一 `ApiResponse[T]` 响应封装约定、实时路径 IP/会话限流、`UpstreamUnavailableException` 与数据不适用/缺失边界到业务错误态的映射。

### Modified Capabilities

<!-- 无：openspec/specs/ 目前为空，本 change 全部为新增能力；复用 poly-data-integration 与 bias-algorithm 的既有契约，不修改其 spec。 -->

## Impact

- 后端新增：`api/v1` 路由模块（events / rankings）、组合层 `services`（编排 `MarketDataService` → `bias-scoring` 计算 → 装配响应）、对外响应 `schemas`、实时限流 Redis 能力（`services`，经 `core/redis_client`）、新增 `UpstreamUnavailableException` 等业务异常（若 `poly-data-integration` 未落地则在本 change 于 `core/exceptions` 补充并分配业务 code）。
- 依赖分层：`api → services → repositories → models`；本 change 落在 `api`（路由）与 `services`（组合编排 + 限流），消费 `poly-data-integration` 的 `MarketDataService` 缓存读取方法与 `bias-algorithm` 的 `services` 计算函数，不反向依赖、不下沉到 `repositories` 重复实现数据访问。
- 配置：实时路径限流窗口/阈值、排行默认 `top_n`、默认列表 `page_size` 上限经 `core/config.Settings` 从 `.env` 读取，同步补 `.env.example`。
- 无 Postgres 表变更、无 Alembic 迁移（分析结果为 Redis 快照 + 实时计算，不落库）。
- 上游依赖：`poly-data-integration`（`market-data-model` / 缓存读取 / `UpstreamUnavailableException`）与 `bias-algorithm`（`bias-scoring` 计算与排行分档口径）必须先落地本 change 才能集成；契约按二者 artifacts 复用，不自拟。
- 下游契约：前端 change（`event-list-and-input` / `single-event-detail` / `bias-ranking`）消费本 change 提供的接口，本 change **不实现任何前端页**。
