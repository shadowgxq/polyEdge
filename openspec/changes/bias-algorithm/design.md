## Context

PRD §5.1 将偏差评分与三分类的完整口径下放给 `bias-algorithm.md`；PRD §1.3 明确偏差为**纯规则计算**（不引入 AI/LLM，保证可复现、可审计）。后端负责拉取 Polymarket、字段归一并输出已算好的分析结果（PRD §1.4）。本 change 只承担其中的**纯计算**部分：给定已归一化的事件/选项输入，按 bias-algorithm §3–§7 算出每个选项的 `bias_i` 与三分类标签，并给出排行分档口径。

本 change 是**后端单端纯计算**，放在 `backend/` 的 `services` 层（依据 CLAUDE.md「纯计算模块放 services 层」与后端分层规范）。不涉及路由、数据库表、迁移、对外接口。上游 `poly-data-integration` 提供选项级归一化字段、下游 `analysis-api` 消费本模块输出，两者与本 change 并行；本 change 通过自定义**输入契约**与上游解耦，从而可独立单测。

## Goals / Non-Goals

**Goals:**
- 忠实实现 bias-algorithm §3 全链路公式（`p_i`/`trade_i`/`social_i`/`h_i`/`hs_i`/`d_i`/`bias_i`），公式与默认参数**逐条锚定文档，不自拟算法**。
- 钉死数值语义：`norm` 份额型、`round` 半值向上进位、`clamp` 到 `[-100,100]`、三分类阈值 `T`、排行分档互斥无交集。
- 覆盖降级与边界：参与数据退化、除零兜底、无效选项排除后重归一。
- 参数可配置（bias-algorithm §7），`norm` 非可配置。
- 提供黄金 fixture 回归测试（bias-algorithm §8、PRD AC-3）作为算法回归基准。
- 定义最小输入契约，使计算模块可脱离真实 API 独立单测。

**Non-Goals:**
- 不做 Polymarket 拉取与字段归一（属 `poly-data-integration`）。
- 不做对外接口 / 路由 / 缓存 / 限流（属 `analysis-api`，PRD §5、data-source §4/§5）。
- 不做前端展示、i18n 渲染（标签文案的 zh/en 两套由本模块产出 key/文案，界面渲染在前端 change）。
- 不引入订单簿深度实际接入（`w_depth` 默认 0，仅预留参数位，bias-algorithm §3.2/§7）。

## Decisions

### D1. 模块定位与分层
纯计算模块置于 `backend/` `services` 层（如 `services/bias_scoring/`）。计算为无副作用纯函数（输入 → 输出），不依赖 `repositories`/DB/Redis/网络。理由：符合 CLAUDE.md 依赖只向下、纯计算放 services；无副作用便于黄金 fixture 单测。

### D2. 输入契约（对上游的最小假设）
本模块定义自己的输入数据结构（Pydantic v2 或 dataclass，模块内部结构，非对外 API schema），字段锚定 bias-algorithm §2 / data-source §2：
- 选项级：`price`、`volume`、`liquidity`、`volume24hr`、`traders`（per-option 参与/持仓人数，`traders`/`holders` 之一，可为 `None`）、可选 `depth`。
- 事件级：选项集合 + 事件级 `commentCount`（仅透传作关注度标签，**不参与单选项偏差**，bias-algorithm §2）。
- **契约假设标注**：上述选项级字段为 `poly-data-integration` 归一化后产物；`traders` 字段的真实可得性由技术方案 API 探针固化（bias-algorithm §3.3 / data-source §2），本模块只按「缺失/`null` = 无、`0` = 有效 0」谓词处理（bias-algorithm §3.5），不假设其一定可得。

### D3. 归一函数 `norm`（钉死，非可配置）
`norm(x_i) = x_i / Σ_j x_j`（份额型，bias-algorithm §3.2）。除零兜底：当分量全 0 或 `Σ_j x_j = 0` 时，该分量对所有选项记 0（bias-algorithm §3.2）。作为唯一实现，不开放配置。理由：文档 §7 明确 `norm` 已钉死、同事件内口径一致。

### D4. 计算主链路（严格按 bias-algorithm §3 顺序）
1. `p_i = price_i / Σ price_j`（§3.1；`Σ price_j = 0` → 事件不适用，见 D6）。
2. `turnover_i = clamp(volume24hr_i / volume_i, 0, 1)`（`volume_i = 0` 记 0，§3.2）。
3. `trade_i = w_vol·norm(volume) + w_liq·norm(liquidity) + w_24h·norm(volume24hr) + w_turn·norm(turnover)`（+ 可选 `w_depth·norm(depth)`，默认 0）（§3.2）。
4. `social_i = norm(traders_i)`（§3.3），仅当事件未触发退化。
5. `h_i = α·trade_i + β·social_i`；退化时 `h_i = trade_i`（等价 β=0）（§3.4/§3.5）。
6. `hs_i = h_i / Σ h_j`；`Σ h_j = 0` → `hs_i = 1/n` 均分（§3.6）。
7. `d_i = hs_i − p_i`；`bias_i = clamp(round(d_i·100), −100, 100)`（§3.7）。

### D5. `round` 半值向上进位（round half up）
自实现 round-half-away-from-zero：`14.5 → 15`、`−14.5 → −15`，不用 Python 内建 `round`（banker's rounding）。理由：bias-algorithm §3.7 明确固定该规则以保证边界样例可复现。实现建议用 `decimal.Decimal(...).quantize(ROUND_HALF_UP)` 对 `d_i·100` 定点进位（对负值取 `ROUND_HALF_UP` 即远离零方向）。

### D6. 数据退化与适用性边界（bias-algorithm §3.5 / §6）
- **参与数据退化（混合退化口径）**：事件内**任一选项** `traders` 缺失/`null` → **全事件**退化为纯交易热度（所有选项 `h_i = trade_i`），并在输出标注 `degraded_trade_only = true`（前端据此显示「纯交易热度」）。值 `0` 视为有效 0，不触发退化。
- **无效选项排除后重归一**：价格全 0 / 数据缺失的选项排除出计算并标注；`p_i`（§3.1）与 `hs_i`（§3.6）在**剩余有效选项集**上重新归一，使 Σ=1（§6）。
- **不适用偏差**：事件仅 1 个有效选项 / `Σ price_j = 0` → 标注「不适用偏差分析」，只透传原始数据、不产出 `bias_i`（§6、PRD §5.2）。

### D7. 三分类与排行分档（bias-algorithm §4 / §5）
- 三分类阈值 `T`（默认 15）：`bias_i ≥ +T` → 泡沫风险；`bias_i ≤ −T` → 冷门机会；`−T < bias_i < +T` → 合理。标签同时产出 zh/en 两套文案（§4，供前端 i18n，PRD §5.4）。
- 排行分档与 `±T` 对齐、互斥无交集（§5）：泡沫榜 `bias_i ≥ +T` 降序、冷门榜 `bias_i ≤ −T` 升序、合理列表 `|bias_i| < T`；每选项恰落入且仅落入一档。榜单项保留事件归属（供回跳）。TopN 截取属对外接口层（`analysis-api`），本模块只给全量分档口径。

### D8. 参数配置（bias-algorithm §7）
可配置：`α/β`（默认 0.7/0.3）、`w_vol/w_liq/w_24h/w_turn`（各 1/4）、`w_depth`（默认 0）、`T`（默认 15）。以带默认值的参数对象传入计算函数（默认值即 §7 默认）。业务可调项与敏感配置无关，默认值内聚在模块常量；不硬编码在计算逻辑分支里。`norm` 不在可配置集内。

### D9. 黄金 fixture 作为回归基准（bias-algorithm §8、PRD AC-3）
以数据文件（如 JSON）承载「固定输入 → 期望 `bias_i` / 标签」样例，单测逐条断言。样例覆盖 §8 全部七类：正常多选项、阈值边界（`+15`/`−15`/`14`）、round 半值边界（`14.5→15`、`−14.5→−15`）、clamp 边界、除零兜底（分量 Σ=0 / Σh=0 / volume=0）、参与数据退化、排除后重归一。具体数值在本 change 规格/实现阶段固化（§8 要求），一经确定即为回归基准，改动须同步更新样例与预期。

## Risks / Trade-offs

- [黄金 fixture 数值需人工精算，易与实现口径不一致] → 用 D4/D5 定点规则手算并交叉核对；round 半值与 clamp 边界样例单列，防 banker's rounding 回归。
- [上游 `traders` 字段可得性未定（bias-algorithm §3.3 待 API 探针固化）] → 本模块以退化谓词兜底，两条路径（有 social / 纯交易）都由 fixture 覆盖，字段是否可得不阻塞本 change。
- [输入契约与 `poly-data-integration` 归一化产物字段名可能不完全一致] → 契约按 bias-algorithm §2 / data-source §2 命名，作为「依赖上游提供选项级归一化字段」的假设标注；如上游字段名不同，由适配层在集成时对齐，不改计算口径。
- [多 outcome market 的 volume/liquidity 可能仅 market 级、无法拆到选项（data-source §2）] → 该分量按缺失兜底（D3 除零兜底）并可标注口径限制，属输入契约边界；本模块不负责拆分/估算。
- [`round`/浮点精度导致边界样例跨语言不可复现] → D5 用 Decimal 定点 `ROUND_HALF_UP`，避免二进制浮点在 `.5` 边界抖动。

## Migration Plan

无数据库变更、无迁移、无对外接口。纯新增 `services` 层模块 + 单测 + fixture 数据文件，可直接随后端部署上线；回滚即移除模块，无状态残留。下游 `analysis-api` 在其 change 内接入本模块输出。

## Open Questions

- `traders` 与 `holders` 二者以哪个为主取参与度代理，待 `poly-data-integration` API 探针固化（bias-algorithm §3.3）；本模块只依赖「单一 per-option 参与数」这一抽象，不阻塞。
- 黄金 fixture 的具体数值集在实现阶段最终固化（bias-algorithm §8 明确「数值待规格阶段固化」），本 change 负责产出并锁定。
