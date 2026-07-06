# 偏差算法业务规则

> 本文档定义 Polymarket-only 的「关注结构偏差」口径，是 [PRD.md](./PRD.md) 第 5.1 节的展开。字段来源见 [data-source.md](./data-source.md)。

## 1. 总体思路

本算法不预测真实胜率，也不判断某选项相对真实概率是否便宜或昂贵。只使用 Polymarket 自身可观测数据：

- 先用市场价格确定身份：热门 / 中位 / 冷门。
- 再用成交、流动性、动量、盘口判断关注度是否异常。
- 最后输出内部可验证的结构标签：低关注热门、过热热门、观察冷门等。

诚实边界：

- 价格就是 Polymarket 当前市场概率；没有外部公平概率时，不能从价格和热度反推出真实价值。
- 标签和文案不得宣称相对真实概率的高估或低估。
- “低关注”只是关注结构信号，不等于买入机会。

## 2. 免费可取数据

2026-07-06 通过 Gamma `/events` 探针确认，世界杯冠军事件一次请求即可拿到候选项级字段：

```text
outcomePrices
volume
volume24hr
volume1wk
volume1mo
liquidity
spread
bestBid
bestAsk
oneDayPriceChange
oneWeekPriceChange
competitive
clobTokenIds
conditionId
```

同一响应里 `numTraders` / `openInterest` 不稳定，不作为 P0。MVP 不新增社交平台、博彩、Elo、CLOB book 深度等外部请求。

## 3. 输入量

| 量 | 说明 | 必需性 |
| --- | --- | --- |
| `price_i` | 选项当前价格，近似隐含概率 | P0 |
| `volume_i` | 累计成交量 | P0，可缺失兜底 |
| `liquidity_i` | 流动性 | P0，可缺失兜底 |
| `volume24hr_i` | 24h 成交量 | P0，可缺失兜底 |
| `volume1wk_i` | 近 1 周成交量 | P0，可缺失兜底 |
| `one_day_price_change_i` | 1 日价格变化 | P0，可缺失兜底 |
| `spread_i` | 买卖价差 | P0，可缺失兜底 |
| `traders_i` | per-option 参与人数，仅可得时使用 | P2 |
| `commentCount` | 事件级评论数，仅展示 | P2 |

`commentCount` 是事件级字段，不区分选项，不参与单选项偏差计算。

## 4. 概率份额

偏差只在单个事件内部比较。

```text
p_i = price_i / Σ_j price_j
```

适配两种结构：

- 单 market 多 outcome：选项 = 各 outcome。
- 多个 Yes/No 子 market 组成的事件：选项 = 各子 market 的 Yes 侧，例如 World Cup Winner 下每支球队一个选项。

若有效选项少于 2 个，或所有价格无效，该事件不适用偏差分析。

## 5. L0 Attention

交易关注度优先使用免费 Gamma 字段，默认不依赖社媒或交易人数。

```text
turnover_i = clamp(volume24hr_i / volume_i, 0, 1)

attention_i =
  0.00 * norm(volume_i)
+ 0.10 * norm(liquidity_i)
+ 0.45 * norm(volume24hr_i)
+ 0.25 * norm(volume1wk_i)
+ 0.20 * norm(turnover_i)
```

解释：

- `volume_i` 默认权重 0：累计成交量容易代表历史沉淀，不适合直接当实时关注。
- `volume24hr_i` 和 `volume1wk_i` 是核心，兼顾短期爆发和近周持续度。
- `turnover_i` 捕捉近期成交相对自身体量的活跃度。
- `liquidity_i` 权重较低，只作为可交易性和关注基础的辅助项。

归一函数固定：

```text
norm(x_i) = x_i / Σ_j x_j
```

某分量全 0 或缺失时，该分量对所有选项记 0，不产生 NaN。

## 6. 参与热度退化

若全部有效选项都有 `traders_i`，可按旧口径合成：

```text
social_i = norm(traders_i)
h_i = α * attention_i + β * social_i
默认 α = 0.7, β = 0.3
```

但当前 Gamma `/events` 的 per-option 参与人数不可稳定依赖。因此任一有效选项 `traders_i` 缺失时，全事件退化为：

```text
h_i = attention_i
```

值为 `0` 是有效 0；缺失或 `null` 才触发退化。

## 7. 热度份额与保留 bias

```text
hs_i = h_i / Σ_j h_j
d_i = hs_i - p_i
bias_i = clamp(round_half_up(d_i * 100), -100, 100)
```

`bias_i` 保留旧数值口径，用于展示“热度份额相对价格份额的差”。它不直接决定“冷门机会”。

当 `Σ_j h_j = 0` 时，`hs_i = 1 / n` 均分。

## 8. 非线性预期关注度

热门天然更容易吸收关注，但关注度不应按价格线性增长。因此标签判断使用非线性预期关注：

```text
ExpectedAttention_i = norm(p_i ^ gamma)
attention_residual_i = hs_i - ExpectedAttention_i
默认 gamma = 0.65
```

注意：

- `bias_i` 仍为 `hs_i - p_i`。
- 过热/低关注标签用 `attention_residual_i`。
- 这能避免 France 这类 32.8% 头号热门只因没有拿到 32.8% 热度份额就被过度惩罚。

## 9. 身份池

身份只由市场概率决定，不由热度决定。

```text
rank_i = 1 + count(p_j > p_i)

if rank_i <= 3 or p_i >= 0.20:
  pool = favorite
elif p_i < 0.08:
  pool = longshot
else:
  pool = contender
```

关键规则：

- 只有 `longshot` 池可以输出冷门类标签。
- `favorite` 池即使低关注，也只能输出“低关注热门”，不能输出冷门。

## 10. 多信号

```text
momentum_i = clamp(one_day_price_change_i / 0.10, -1, 1)
fragility_i = clamp((spread_i / max(price_i, ε)) / 0.05, 0, 1)
acceleration_i = clamp(volume24hr_i / (volume1wk_i / 7 + ε) - 1, -1, 1)
```

缺失字段按 0 兜底，不臆造。

## 11. 过热分与观察分

过热分：

```text
overheat_score =
100 * clamp(
  0.40 * max(attention_residual_i, 0) / 0.20
+ 0.30 * max(momentum_i, 0)
+ 0.15 * fragility_i
+ 0.15 * max(acceleration_i, 0),
0, 1)
```

观察分仅对 `longshot` 池计算：

```text
liquidity_health_i = clamp(0.5 * (1 - fragility_i) + 0.5 * min(norm(liquidity_i) * n, 1), 0, 1)
has_volume_i = 1 if volume_i > 0 or volume24hr_i > 0 else 0

watch_score =
100 * clamp(
  0.40 * liquidity_health_i
+ 0.20 * max(momentum_i, 0)
+ 0.30 * (1 - fragility_i)
+ 0.10 * has_volume_i,
0, 1)
```

非 `longshot` 池的 `watch_score` 为空。

## 12. 八类标签

默认阈值：

```text
T = 15
overheat_hi = 60
watch_hi = 55
```

| 身份池 | 条件 | 标签 |
| --- | --- | --- |
| favorite | `overheat_score >= 60` | 过热热门 |
| favorite | `attention_residual_i * 100 <= -T` | 低关注热门 |
| favorite | 其他 | 共识热门 |
| contender | `overheat_score >= 60` | 过热中位 |
| contender | 其他 | 中位竞争者 |
| longshot | `attention_residual_i * 100 >= T` | 被炒作冷门 |
| longshot | `watch_score >= 55` | 观察冷门 |
| longshot | 其他 | 普通冷门 |

标签语义：

- 低关注热门：市场概率高，但当前交易关注低于该身份预期。
- 过热热门 / 过热中位：关注、正动量、脆弱度、加速等结构信号偏热。
- 被炒作冷门：低概率选项的关注度明显高于其预期关注。
- 观察冷门：低概率选项不拥挤，但流动性和盘口结构尚可，值得观察，不代表价值保证。

## 13. 多事件排行

字段名可兼容旧 API，但榜别语义如下：

- 过热榜：过热热门 + 过热中位 + 被炒作冷门，按 `overheat_score` 降序。
- 观察榜：观察冷门 + 低关注热门，按 `watch_score`、`abs(bias_i)` 降序。
- 合理：共识热门 + 中位竞争者 + 普通冷门。

三榜互斥无交集。

## 14. France 示例

真实探针样本中 France：

```text
price = 0.3275
rank = 1
volume24hr ≈ 1,780,159
volume1wk ≈ 17,415,684
liquidity ≈ 8,168,880
spread = 0.001
oneDayPriceChange = -0.026
```

计算结果：

```text
pool = favorite
bias ≈ -24 至 -28（随同事件候选集合变化）
category = 低关注热门
```

解释：

France 是市场概率最高的热门选项，但交易关注度低于其热门身份的预期，所以标记为“低关注热门”。这不是冷门机会，也不是价值判断。

## 15. 参数汇总

| 参数 | 默认值 |
| --- | --- |
| `α / β` | 0.7 / 0.3 |
| `w_vol / w_liq / w_24h / w_1wk / w_turn` | 0 / 0.10 / 0.45 / 0.25 / 0.20 |
| `w_depth` | 0 |
| `favorite_rank_max` | 3 |
| `favorite_prob_min` | 0.20 |
| `longshot_prob_max` | 0.08 |
| `attention_expectation_gamma` | 0.65 |
| `momentum_ref` | 0.10 |
| `spread_ref` | 0.05 |
| `crowd_ref` | 0.20 |
| `threshold_t` | 15 |
| `overheat_hi` | 60 |
| `watch_hi` | 55 |

## 16. 验收样例

黄金 fixture 覆盖：

- 正常多选项与 `bias_i` 数值稳定。
- 阈值边界和 round half up。
- 无效选项排除后重归一。
- 参与数据缺失后的纯交易热度退化。
- 头号热门低关注不被判为冷门。
- 过热热门、被炒作冷门、观察冷门、普通冷门。
- 白拿字段缺失时多信号退化为中性。
