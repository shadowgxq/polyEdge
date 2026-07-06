## Why

当前偏差算法只用「热度份额 hs − 概率份额 p」一个残差，且无身份闸门：头号热门 France（p 32.7%）因交易热度没跟上高定价就被误标「低热度·冷门机会」，语义反直觉、误导用户。同时 `/events` 响应里的价格动量、盘口、多窗口成交量等字段被白白丢弃，信号单薄。本次在**零新上游请求**下把它升级为多信号 + 身份分层 + 诚实标签。

诚实底线：只用 Polymarket 数据无法证明「相对真实概率的高估/低估」（价格即市场概率，反推公平概率是循环论证）。故本次只产出**内部可验证**的结构信号（拥挤、过热、值得观察），标签与文案**不得出现「高估/低估」字样**；真·价值判断需外部公平概率，属另一轴、不在本次范围。

## What Changes

- 数据接入（零新请求，同 `/events` 响应白拿）：`market-data-model` 选项级新增 `one_day_price_change`/`one_week_price_change`/`best_bid`/`best_ask`/`spread`/`volume1wk`/`volume1mo`/`competitive`；`polymarket-client` 映射；`market-data-cache` 缓存两层白名单同步。
- 算法（`bias-scoring`）：`bias=(hs−p)×100` 数值不变，语义改称「交易集中度残差 crowding」；新增身份池（热门/中位/冷门）、价格动量、流动性脆弱度、成交加速信号，以及 `overheat_score`（过热分）、`watch_score`（观察分）两个复合分。
- 三分类扩为 **8 类诚实标签**：共识热门 / 低关注热门 / 过热热门 / 中位竞争者 / 过热中位 / 普通冷门 / 被炒作冷门 / 观察冷门。身份闸门确保热门池不再输出「冷门」类。
- 契约（`analysis-event-api`/`analysis-ranking-api`）：`OptionAnalysis`/`RankingItem` 新增可选信号字段（`pool`/`momentum`/`fragility`/`overheat_score`/`watch_score`），`label` 承载 8 类细文案。全部向后兼容加字段。
- 排行（`bias-ranking-view`）：三榜诚实重定义为 **过热榜 / 观察榜 / 合理**；排行项渲染各自细标签文案。
- **BREAKING**（口径层）：偏差三分类语义由「泡沫/冷门/合理」改为 8 类诚实标签；`docs/prd/polymarket-bias-detector/bias-algorithm.md` 同步更新。对外 API 为纯增量加字段，不破坏字段结构。

## Capabilities

### New Capabilities
<!-- 无新增 capability；全部为既有能力的口径/字段扩展。 -->

### Modified Capabilities
- `bias-scoring`: 偏差评分口径由单残差三分类扩为「身份池 × 多信号（拥挤/动量/脆弱/加速）× overheat/watch 复合分」的 8 类诚实标签；新增业务可调参数；明确「无高估/低估宣称」诚实边界；`bias` 数值口径不变。
- `market-data-model`: 选项级归一化模型新增动量/盘口/多窗口成交量/竞争度字段（可空，向后兼容）。
- `polymarket-client`: 从既有 Gamma `/events` 响应额外映射上述白拿字段，无新增端点调用。
- `market-data-cache`: Redis 分层缓存白名单与 `_merge_event` 同步新增字段（波动量入短 TTL 价格层、慢变量入长 TTL 元数据层）。
- `analysis-event-api`: 事件明细/卡片出参新增可选信号字段，`overview_label`/`label` 承载 8 类诚实标签文案。
- `analysis-ranking-api`: 榜单项出参新增可选信号字段并承载细标签文案。
- `bias-ranking-view`: 三榜语义诚实重定义（过热榜/观察榜/合理），排行项按各自细标签渲染与上色。

## Impact

- 后端：`app/schemas/market_data.py`、`app/repositories/polymarket_client.py`、`app/repositories/market_data_cache_repository.py`、`app/services/bias_scoring/{contracts,params,calculator,labels,results,ranking}.py`、`app/schemas/analysis.py`、`app/services/analysis_service.py`。
- 前端：`pages/bias-ranking/*`（榜别标题、细标签渲染）、三模块 DTO/api 转换、`shared/i18n/resources`；卡片/单事件页因原样渲染后端文案预计零运行时改动。
- 测试：`tests/fixtures/bias_golden.json`（category 重算 + 新增用例）、`tests/test_bias_scoring.py`、`tests/test_analysis_api.py`、前端排行测试。
- 数据：`MarketOption`/`MarketEvent` 新字段可空 → 无 Alembic 迁移；旧快照向后兼容。
- 文档：`docs/prd/polymarket-bias-detector/bias-algorithm.md` 回锚更新。
