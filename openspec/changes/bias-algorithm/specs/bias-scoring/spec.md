## ADDED Requirements

### Requirement: 概率份额计算（p_i）

系统 SHALL 在单个事件的选项集合内，将各选项价格归一化得到概率份额 `p_i = price_i / Σ_j price_j`，使 Σ p_i = 1。作用域为单事件（单 market 多 outcome 或多 market 组成事件均按 bias-algorithm §3.1 统一处理）。来源：PRD §5.1、bias-algorithm §3.1。

#### Scenario: 多选项概率份额归一

- **WHEN** 一个事件含多个有效选项且 Σ_j price_j > 0
- **THEN** 每个选项输出 `p_i = price_i / Σ_j price_j`，且所有 p_i 之和为 1

#### Scenario: 价格总和为零不适用

- **WHEN** 事件内 Σ_j price_j = 0
- **THEN** 该事件标注「不适用偏差分析」，不产出 p_i / bias_i（见「适用性边界」要求）

### Requirement: 交易热度计算（trade_i）

系统 SHALL 对成交量、流动性、24h 成交量、换手率四项分别做事件内份额型归一 `norm` 后加权合成 `trade_i`，默认四项等权 `w_vol = w_liq = w_24h = w_turn = 1/4`；换手率 `turnover_i = clamp(volume24hr_i / volume_i, 0, 1)`（`volume_i = 0` 时该项记 0）。可选订单簿深度项 `w_depth·norm(depth_i)` 默认 `w_depth = 0`（MVP 不启用）。来源：PRD §5.1、bias-algorithm §3.2。

#### Scenario: 四项份额加权合成

- **WHEN** 事件内各选项具备 volume / liquidity / volume24hr 数据
- **THEN** 每项经 `norm(x_i) = x_i / Σ_j x_j` 归一后按权重合成 `trade_i = w_vol·norm(volume) + w_liq·norm(liquidity) + w_24h·norm(volume24hr) + w_turn·norm(turnover)`

#### Scenario: 换手率截断

- **WHEN** 某选项 volume24hr_i > volume_i（脏数据）
- **THEN** `turnover_i` 被截断为 1；当 volume_i = 0 时 `turnover_i` 记 0

#### Scenario: 深度项默认关闭

- **WHEN** 未显式配置 `w_depth`
- **THEN** `w_depth = 0`，深度不参与 trade_i 合成，接口保留可开

### Requirement: 归一函数 norm（份额型，钉死）

系统 SHALL 将归一函数固定为份额型 `norm(x_i) = x_i / Σ_j x_j`（除以事件内该分量之和），作为唯一实现且非可配置项。当该分量全为 0 或 `Σ_j x_j = 0` 时，该分量对所有选项记 0，不得产生 NaN。来源：bias-algorithm §3.2、§7。

#### Scenario: 份额型归一

- **WHEN** 对某分量在事件内做 norm 且 Σ_j x_j > 0
- **THEN** 每个选项得到 `x_i / Σ_j x_j`，且所有结果之和为 1

#### Scenario: 分量全零除零兜底

- **WHEN** 某分量在事件内 Σ_j x_j = 0
- **THEN** 该分量对所有选项记 0，不产生 NaN

### Requirement: 参与/持仓热度计算（social_i）

系统 SHALL 以 per-option 交易者/持仓人数（`traders_i` / `holders_i`，平台内参与代理指标，非社媒信号）做事件内份额型归一 `social_i = norm(traders_i)`。判定谓词：该字段**缺失或为 `null`** 视为「无」（触发退化，见「数据退化规则」）；值为 **`0`** 视为有效 0（正常参与归一，不触发退化）。来源：PRD §5.1/§5.2、bias-algorithm §3.3、data-source §2。

#### Scenario: 参与数据可得时归一

- **WHEN** 事件内所有选项均具备 per-option 参与/持仓人数（含值为 0）
- **THEN** 每个选项输出 `social_i = norm(traders_i)`

#### Scenario: 值为零视为有效

- **WHEN** 某选项 traders_i = 0 而其余选项字段均存在
- **THEN** 不触发退化，该选项 social 份额按有效 0 参与归一

### Requirement: 热度合成与热度份额（h_i / hs_i）

系统 SHALL 计算热度合成分 `h_i = α·trade_i + β·social_i`（默认 α = 0.7、β = 0.3）与热度份额 `hs_i = h_i / Σ_j h_j`（Σ hs_i = 1）。当 `Σ_j h_j = 0` 时 `hs_i` 按选项数均分（`hs_i = 1/n`），不得产生 NaN。来源：bias-algorithm §3.4、§3.6。

#### Scenario: 热度合成与份额归一

- **WHEN** 事件内各选项已得 trade_i 与 social_i 且 Σ_j h_j > 0
- **THEN** 输出 `h_i = α·trade_i + β·social_i` 与 `hs_i = h_i / Σ_j h_j`，且所有 hs_i 之和为 1

#### Scenario: 热度总和为零均分

- **WHEN** 事件内所有选项 h_i = 0（Σ_j h_j = 0）
- **THEN** 每个选项 `hs_i = 1/n`（n 为有效选项数），不产生 NaN

### Requirement: 偏差评分计算（bias_i）

系统 SHALL 计算偏差 `d_i = hs_i − p_i`（范围 [-1,1]、Σ d_i = 0）与偏差评分 `bias_i = clamp(round(d_i · 100), −100, 100)`。`round` MUST 采用半值向上进位（round half away from zero）：`14.5 → 15`、`−14.5 → −15`，不得使用 banker's rounding。`bias_i` MUST clamp 到 `[−100, 100]`。来源：bias-algorithm §3.7。

#### Scenario: 偏差评分映射

- **WHEN** 某选项得到 hs_i 与 p_i
- **THEN** 输出 `bias_i = clamp(round((hs_i − p_i) · 100), −100, 100)`

#### Scenario: round 半值向上进位

- **WHEN** `d_i · 100 = 14.5` 或 `d_i · 100 = −14.5`
- **THEN** 分别进位为 `15` 与 `−15`（远离零方向），不因库默认 banker's rounding 得到 14 / −14

#### Scenario: clamp 边界截断

- **WHEN** `d_i · 100` 超出 [−100, 100]
- **THEN** `bias_i` 被截断到 −100 或 100

### Requirement: 偏差三分类标签（阈值 T，中英两套）

系统 SHALL 以阈值 `T`（默认 15）对 `bias_i` 三分类，三档互斥无交集：`bias_i ≥ +T` → 高热度·泡沫风险（Overheated · Bubble Risk）；`bias_i ≤ −T` → 低热度·冷门机会（Underhyped · Value Opportunity）；`−T < bias_i < +T` → 合理（Fairly Priced）。每个标签 MUST 同时产出中文与英文两套文案供 i18n。来源：PRD §5.4/AC-8、bias-algorithm §4。

#### Scenario: 恰达阈值入泡沫

- **WHEN** `bias_i = +15`（T 默认 15，`bias_i ≥ +T`）
- **THEN** 分类为「高热度·泡沫风险 / Overheated · Bubble Risk」

#### Scenario: 恰达阈值入冷门

- **WHEN** `bias_i = −15`（`bias_i ≤ −T`）
- **THEN** 分类为「低热度·冷门机会 / Underhyped · Value Opportunity」

#### Scenario: 阈值内为合理

- **WHEN** `bias_i = 14`（`−T < bias_i < +T`）
- **THEN** 分类为「合理 / Fairly Priced」

#### Scenario: 中英两套文案

- **WHEN** 输出任一选项的偏差标签
- **THEN** 同时给出中文与英文文案，供前端按当前语言渲染

### Requirement: 数据退化规则（混合退化为纯交易热度）

系统 SHALL 采用混合退化口径：事件内**任一选项**缺 per-option 参与数据（字段缺失或为 `null`）时，**全事件**退化为纯交易热度（对所有选项 `h_i = trade_i`，等价 β=0），并在输出标注退化状态供前端显示「纯交易热度」。值为 `0` 不触发退化。来源：PRD §5.2、bias-algorithm §3.3/§3.5。

#### Scenario: 任一选项缺参与数据全事件退化

- **WHEN** 事件内至少一个选项的 per-option 参与字段缺失或为 null
- **THEN** 该事件所有选项按 `h_i = trade_i` 计算，输出标注退化为纯交易热度

#### Scenario: 全部具备参与数据不退化

- **WHEN** 事件内所有选项均具备 per-option 参与字段（含值 0）
- **THEN** 不退化，按 `h_i = α·trade_i + β·social_i` 计算

### Requirement: 适用性边界与无效选项重归一

系统 SHALL 处理适用性边界：事件仅 1 个有效选项或缺价格（`Σ_j price_j = 0`）时标注「不适用偏差分析」，仅透传原始数据、不产出 bias_i；价格全为 0 或数据缺失的选项排除出偏差计算并标注，排除后 `p_i` 与 `hs_i` 在**剩余有效选项集**上重新归一使 Σ 仍为 1。来源：PRD §5.2、bias-algorithm §3.5/§6。

#### Scenario: 单选项不适用

- **WHEN** 事件仅含 1 个有效选项
- **THEN** 标注「不适用偏差分析」，只展示原始数据，不计算事件内相对偏差

#### Scenario: 无效选项排除后重归一

- **WHEN** 事件内某选项价格全为 0 / 数据缺失
- **THEN** 该选项被排除并标注，p_i 与 hs_i 在剩余有效选项集上重新归一，其和仍为 1

### Requirement: 多事件排行分档口径

系统 SHALL 对一组事件的所有选项各自计算 `bias_i`（仍在其所属事件内归一），并按与三分类阈值 `T` 对齐且互斥无交集的口径分档：泡沫风险榜 `bias_i ≥ +T`（按 bias_i 降序）、冷门机会榜 `bias_i ≤ −T`（按 bias_i 升序）、合理列表 `|bias_i| < T`；每个选项恰落入且仅落入一档，无交集无遗漏，且每条榜单项保留其事件归属。来源：PRD §4.4/AC-4、bias-algorithm §5。

#### Scenario: 三档互斥无交集

- **WHEN** 对一组事件的所有选项分档
- **THEN** 每个选项按其 bias_i 相对 ±T 的位置恰落入泡沫榜 / 冷门榜 / 合理列表之一，三者无交集、无遗漏

#### Scenario: 榜单排序与事件归属

- **WHEN** 生成泡沫风险榜与冷门机会榜
- **THEN** 泡沫榜按 bias_i 降序、冷门榜按 bias_i 升序，每项保留所属事件归属以便回跳

### Requirement: 可配置参数

系统 SHALL 支持业务可调参数：`α / β`（默认 0.7 / 0.3）、`w_vol / w_liq / w_24h / w_turn`（各 1/4）、`w_depth`（默认 0）、`T`（默认 15）；调整参数不改变算法语义。归一函数 `norm` MUST 保持份额型钉死、不可配置。来源：bias-algorithm §7。

#### Scenario: 使用默认参数

- **WHEN** 未显式传入参数
- **THEN** 采用 α=0.7、β=0.3、四项权重各 1/4、w_depth=0、T=15

#### Scenario: 覆盖参数不改语义

- **WHEN** 传入自定义 α/β、四项权重或 T
- **THEN** 按新参数计算，但计算步骤、norm 份额型口径与三分类结构不变

### Requirement: 黄金 fixture 回归基准

系统 SHALL 提供一组固定输入 → 期望 `bias_i` / 标签的黄金 fixture 作为算法回归基准，单测逐条断言。fixture MUST 覆盖：正常多选项、阈值边界（bias_i = +15 / −15 / 14）、round 半值边界（d_i·100 = 14.5→15 / −14.5→−15）、clamp 边界、除零兜底（分量 Σ=0 / Σh=0 / volume=0）、参与数据退化、排除后重归一。真实 Polymarket 数据仅做冒烟验证。来源：PRD AC-3、bias-algorithm §8。

#### Scenario: 固定输入断言期望输出

- **WHEN** 以 fixture 中的固定输入运行计算
- **THEN** 输出的 bias_i 与三分类标签与 fixture 期望值逐条一致

#### Scenario: 覆盖全部边界用例

- **WHEN** 运行黄金 fixture 回归测试集
- **THEN** 正常多选项、阈值边界、round 半值边界、clamp 边界、除零兜底、参与数据退化、排除后重归一七类用例均有样例且全部通过

#### Scenario: 真实数据仅冒烟

- **WHEN** 以真实 Polymarket 数据运行
- **THEN** 仅做冒烟（不产 NaN / 不抛异常 / 输出结构完整），不以真实数据断言具体 bias_i 数值
