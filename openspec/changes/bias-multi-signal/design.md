## Context

当前 `bias-scoring`（bias-algorithm §3–§5）在单事件内计算 `bias_i=(hs_i−p_i)×100` 后按阈值 T 三分类。缺陷：(1) 无身份闸门，头号热门被误标冷门；(2) 只用交易热度残差一个信号；(3) `traders` 恒 None（Gamma `/events` 无 `numTraders`，data-source §2/§3.6 Open Question 未闭环），算法长期走退化分支、社交维度失效。本次在**零新上游请求**下，用 Gamma `/events` 同响应白拿字段扩信号，并把标签升级为身份分层的诚实体系。锚定 bias-algorithm §3（公式）、§4（分类）、§7（参数可调、归一化钉死）。

## Goals / Non-Goals

**Goals:**
- 身份闸门修正「头号热门被判冷门」（France → 低关注热门）。
- 用零新请求白拿字段引入价格动量、流动性脆弱度、成交加速信号，产出 `overheat_score`/`watch_score` 复合分与 8 类诚实标签。
- 契约纯增量加可选字段，卡片/单事件页零运行时改动即承接新文案。
- 保持 `bias` 数值口径不变，控制 golden 回归面。

**Non-Goals:**
- 不接外部公平概率（博彩去水/Elo），不宣称「相对真实概率的高估/低估」。
- 不修 `traders` bug（不新增 `/holders` 请求），社交/人数维度维持退化。
- 不新增 CLOB `/book` 订单簿深度请求；不建历史时序表。

## Decisions

**D1 诚实边界：只输出内部可验证信号，标签/文案禁用「高估/低估」。** 备选（接外部 FairProbability 做真价值判断）成本高且属另一轴，本次排除。所有标签语义可由 Polymarket 自身 price/volume/liquidity/动量/盘口回溯验证。

**D2 `bias` 数值不变、语义改称「交易集中度残差 crowding」。** 保留 `bias=(hs_i−p_i)×100`（bias-algorithm §7），golden 的 `bias` 期望不动；仅 `category` 由更丰富的决策函数产生。备选（把新信号并入 bias 公式）会牵动全部 golden 数值精算，弃用。

**D3 身份池（bias-algorithm §3 扩展）。** `rank_i = 1 + #{p_j>p_i}`；`FAVORITE` = `rank≤favorite_rank_max(3)` 或 `p_i≥favorite_prob_min(0.20)`；`LONGSHOT` = `p_i<longshot_prob_max(0.08)` 且非 FAVORITE；否则 `CONTENDER`。用归一化 `p_share`（非原始 price），与 bias 同口径、对量纲鲁棒。

**D4 L0 Attention 默认权重以免费 Gamma `/events` 可得字段为准。** `trade_i` 在实现中继续作为内部变量名，但业务语义为 AttentionScore：`w_vol=0`、`w_liq=0.10`、`w_24h=0.45`、`w_1wk=0.25`、`w_turn=0.20`、`w_depth=0`。累计成交量默认不参与实时关注，避免历史成交污染；24h/1w 成交和换手率为核心。Gamma 探针确认 `volume24hr`/`volume1wk`/`liquidity`/`spread`/`bestBid`/`bestAsk`/`oneDayPriceChange`/`oneWeekPriceChange` 可同请求白拿，`numTraders`/`openInterest` 不作为 P0。

**D5 非线性预期关注度用于标签判定。** `ExpectedAttention=normalize(p_i^γ)`，默认 `γ=0.65`；`attention_residual=hs_i−ExpectedAttention_i`。`bias` 仍按 `hs_i−p_i` 输出，避免破坏历史数值口径；分类与过热分使用 `attention_residual`，避免 France 这类头号热门被线性预期过度惩罚。

**D6 新信号纯函数，复用 `norm`/`clamp`，缺失值→0（不臆造）。**
- `momentum_i = clamp(one_day_price_change_i / momentum_ref(0.10), −1, 1)`
- `fragility_i = clamp((spread_i / max(price_i,ε)) / spread_ref(0.05), 0, 1)`
- `acceleration_i = clamp(volume24hr_i/(volume1wk_i/7+ε) − 1, −1, 1)`
- `crowding_i = attention_residual_i`（标签判定用；输出 `bias` 仍为 `(hs_i−p_i)×100`）

**D7 两个复合分（0–100）。**
- `overheat_score = 100·clamp(0.4·max(crowding,0)/crowd_ref(0.20) + 0.3·max(momentum,0) + 0.15·fragility + 0.15·max(acceleration,0), 0, 1)`
- `watch_score = Gate(pool=LONGSHOT)·100·clamp(0.4·liquidity_health + 0.2·max(momentum,0) + 0.3·(1−fragility) + 0.1·has_volume, 0, 1)`，`liquidity_health` 由流动性份额与 `(1−fragility)` 合成，`has_volume∈{0,1}`。

**D8 8 类标签决策函数 `classify_option(pool, crowding, overheat, watch, T, params)`（保留旧 `classify(bias,T)` 供既有测试）：**
FAVORITE：`overheat≥overheat_hi(60)`→过热热门；`crowding≤−T`→低关注热门；else 共识热门。
CONTENDER：`overheat≥overheat_hi`→过热中位；else 中位竞争者。
LONGSHOT：`crowding≥+T`→被炒作冷门；`watch≥watch_hi(55)`→观察冷门；else 普通冷门。

**D9 三榜诚实重定义（bias-ranking-view）。** 过热榜 = 过热热门+过热中位+被炒作冷门（按 overheat 降序）；观察榜 = 观察冷门+低关注热门（按 watch/|bias| 序）；合理 = 共识热门+中位竞争者+普通冷门。

**D10 缓存分层加字段。** 波动量（best_bid/best_ask/spread/one_day_price_change）入短 TTL `price_payload`，慢变量（volume1wk/volume1mo/competitive/one_week_price_change）入长 TTL `meta_payload`，两处白名单 + `_merge_event` 同改（data-source §缓存分层）。

## Risks / Trade-offs

- [行为变化：二元/头部市场基本不再出现「冷门」类] → 符合诚实定位（冷门属长尾），文档与 UI 文案明示口径。
- [golden category 大面积重算] → `bias` 数值不变缩小面；分档用例逐条精算并加注。
- [白拿字段部分事件可能缺失（如新市场无 1w 量/动量）] → 缺失→0 兜底，信号退化为中性、不崩。
- [缓存白名单漏改导致 fresh 读丢字段] → 明确要求 payload 白名单 + `_merge_event` 与 model 三处同改，补 market_data 测试覆盖。
- [新信号阈值为经验值] → 全部落 `BiasParams`（frozen、业务可调，bias-algorithm §7），后续可灰度调参不改代码。
