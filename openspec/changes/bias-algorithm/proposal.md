## Why

PRD §5.1 与 bias-algorithm 全文规定：偏差评分与三分类是**纯规则计算**（可复现、可审计，PRD §1.3 明确不引入 AI/LLM）。当前仓库没有承载这套口径的模块，而 `analysis-api`、`single-event-detail`、`bias-ranking` 等下游 change 都要消费「已算好的偏差结果」（PRD §1.4）。需先把偏差计算沉淀为一个**可独立单测、口径钉死**的后端纯计算 capability，作为全链路事实源。

## What Changes

- 新增后端 `services` 层纯计算模块，实现 bias-algorithm §3 全链路口径：概率份额 `p_i`、交易热度 `trade_i`（成交量/流动性/24h 成交量/换手率四项份额型归一，bias-algorithm §3.2）、参与/持仓热度 `social_i`（平台内 per-option 参与代理指标，非社媒，bias-algorithm §3.3）、热度合成分 `h_i`、热度份额 `hs_i`、偏差 `d_i` 与偏差评分 `bias_i`。
- 钉死数值口径：`round` 半值向上进位（round half up）、`bias_i` clamp 到 `[-100, 100]`、归一函数 `norm` 固定为份额型（除以事件内该分量之和），均按 bias-algorithm §3.7 / §7。
- 实现三分类（bias-algorithm §4，阈值 `T` 默认 15，中/英两套标签）与排行分档口径（bias-algorithm §5，泡沫/冷门/合理三档对齐 `±T`、互斥无交集）。
- 实现降级与边界（bias-algorithm §3.5 / §6）：任一选项缺 per-option 参与数据 → 全事件退化为纯交易热度；除零兜底（分量 Σ=0 / Σh=0 / volume=0）；无效选项（价格全 0 / 数据缺失）排除后剩余有效集重归一。
- 参数（`α/β`、四项权重 `w_vol/w_liq/w_24h/w_turn`、`w_depth`、`T`）可配置（bias-algorithm §7）；`norm` 非可配置项。
- 定义模块自身的**输入契约**（对已归一化事件/选项输入的最小假设），使计算与上游数据拉取解耦、可独立单测。
- 落地黄金 fixture 回归测试（bias-algorithm §8、PRD AC-3）：固定输入 → 期望 `bias_i` / 标签，覆盖正常多选项、阈值边界、round 半值边界、clamp 边界、除零兜底、参与数据退化、排除后重归一七类用例；真实 Polymarket 数据仅冒烟。

## Capabilities

### New Capabilities
- `bias-scoring`: 单事件内「热度份额 vs 概率份额」偏差计算的纯规则口径——`p_i`/`trade_i`/`social_i`/`h_i`/`hs_i`/`bias_i` 全链路、三分类标签（中英）、排行分档、可配置参数、降级与边界处理，以及作为回归基准的黄金 fixture。定义自身输入契约，独立于上游数据拉取与对外接口。

### Modified Capabilities
<!-- 无：greenfield，openspec/specs/ 下暂无既有 capability。 -->

## Impact

- 新增 `backend/` 代码：`services` 层偏差计算模块 + 参数配置（默认值来自 bias-algorithm §7）+ 输入契约 schema（模块内部数据结构，非对外 API 契约）。
- 新增后端单元测试与黄金 fixture 数据（bias-algorithm §8，作为算法回归基准）。
- 无数据库表、无对外接口、无迁移：本 change 为后端单端纯计算。
- 依赖假设：消费 `poly-data-integration` 提供的选项级归一化字段（`price_i`/`volume_i`/`liquidity_i`/`volume24hr_i`/`traders_i` 等）；本 change 以最小输入契约与其解耦，不阻塞其 artifacts。下游 `analysis-api` 消费本模块输出。
