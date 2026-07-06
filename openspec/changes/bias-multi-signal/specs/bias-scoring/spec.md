## ADDED Requirements

### Requirement: 诚实信号边界（不宣称高估/低估）
偏差评分 SHALL 仅基于 Polymarket 自身可观测数据（定价、成交、流动性、动量、盘口）产出内部可验证的结构信号；标签、文案与字段语义 MUST NOT 宣称「相对真实概率的高估/低估」或等义表述。来源：bias-algorithm §4；PRD §5.4。

#### Scenario: 标签文案不含高估/低估语义
- **WHEN** 任一选项被打上三分类之外的新标签
- **THEN** 其中/英文案均不包含「高估/低估/undervalued/overvalued/fair value」等宣称相对真实概率的措辞

### Requirement: 身份池分层
计算 SHALL 依归一化概率份额 `p_i` 与其事件内排名，将有效选项划入 FAVORITE / CONTENDER / LONGSHOT 三池。`rank_i = 1 + #{p_j > p_i}`；`FAVORITE` = `rank_i ≤ favorite_rank_max` 或 `p_i ≥ favorite_prob_min`；`LONGSHOT` = `p_i < longshot_prob_max` 且非 FAVORITE；否则 `CONTENDER`。来源：bias-algorithm §3、§4。

#### Scenario: 头号热门进入 FAVORITE 池且不被判冷门
- **WHEN** 某选项概率份额最高（如 32.7%，rank 1）但交易集中度残差为负
- **THEN** 该选项归入 FAVORITE 池，标签为「低关注热门」而非任何「冷门」类

#### Scenario: 长尾选项进入 LONGSHOT 池
- **WHEN** 某选项 `p_i < longshot_prob_max` 且 rank 靠后
- **THEN** 该选项归入 LONGSHOT 池，方允许输出「观察冷门/被炒作冷门/普通冷门」

### Requirement: L0 Attention 与多信号派生
计算 SHALL 以免费 Gamma `/events` 可得字段合成 L0 Attention：`w_vol=0`、`w_liq=0.10`、`w_24h=0.45`、`w_1wk=0.25`、`w_turn=0.20`。计算 SHALL 为每个有效选项派生 `ExpectedAttention_i=normalize(p_i^gamma)`（默认 `gamma=0.65`）、`attention_residual_i = hs_i − ExpectedAttention_i`、`momentum_i`（源自单日价格变化）、`fragility_i`（源自相对买卖价差）、`acceleration_i`（源自 24h 与周均成交量之比），全部经份额归一/clamp，缺失输入按 0 兜底不臆造。`bias_i=(hs_i−p_i)×100` 数值口径不变。来源：bias-algorithm §5/§8/§10。

#### Scenario: 缺失白拿字段时信号退化为中性
- **WHEN** 某选项缺失单日价格变化 / 价差 / 周成交量
- **THEN** 对应 `momentum/fragility/acceleration` 记 0，计算不产生 NaN 或异常

#### Scenario: bias 数值与既有口径一致
- **WHEN** 对同一输入计算 `bias_i`
- **THEN** 其取值与升级前 `(hs_i−p_i)×100` 四舍五入结果完全一致

### Requirement: 过热分与观察分
计算 SHALL 输出 `overheat_score∈[0,100]`（由 max(attention_residual,0)、max(momentum,0)、fragility、max(acceleration,0) 加权合成）；SHALL 仅对 LONGSHOT 池输出 `watch_score∈[0,100]`（由流动性健康度、正动量、低脆弱度、是否有成交合成），非 LONGSHOT 池 `watch_score` 记 0 或空。来源：bias-algorithm §11。

#### Scenario: 观察分仅对长尾生效
- **WHEN** 选项不属于 LONGSHOT 池
- **THEN** 其 `watch_score` 为 0 或未产出，不参与观察类判定

### Requirement: 八类诚实标签
计算 SHALL 依「身份池 × attention_residual × overheat × watch × 阈值 T」产出八类互斥标签：共识热门 / 低关注热门 / 过热热门 / 中位竞争者 / 过热中位 / 普通冷门 / 被炒作冷门 / 观察冷门，各含中/英双文案。阈值与权重 SHALL 落入 `BiasParams`（业务可调）。旧 `classify(bias,T)` 纯函数 SHALL 保留。来源：bias-algorithm §12、§15。

#### Scenario: FAVORITE 过热
- **WHEN** FAVORITE 池选项 `overheat_score ≥ overheat_hi`
- **THEN** 标签为「过热热门」

#### Scenario: LONGSHOT 观察
- **WHEN** LONGSHOT 池选项 `crowding < +T` 且 `watch_score ≥ watch_hi`
- **THEN** 标签为「观察冷门」，且文案标注非价值保证
