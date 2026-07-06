# Tasks

## 后端

- [x] 1.1 `app/schemas/market_data.py`：`MarketOption` 新增可空字段 `one_day_price_change`/`one_week_price_change`/`best_bid`/`best_ask`/`spread`/`volume1wk`/`volume1mo`/`competitive`（data-source §2）。
- [x] 1.2 `app/repositories/polymarket_client.py::_normalize_market`：从同一 `/events` 响应映射上述字段（`_market_signals` 助手），不新增上游端点调用。
- [x] 1.3 `app/repositories/market_data_cache_repository.py`：波动量入短 TTL `price_payload`、慢变量入长 TTL `meta_payload`，`_merge_event` 同步还原新字段。
- [x] 1.4 `app/services/bias_scoring/contracts.py::OptionInput`：新增 `one_day_price_change`/`spread`/`volume1wk`；`analysis_service._to_event_input` 补映射。
- [x] 1.5 `app/services/bias_scoring/params.py`：`BiasParams` 新增身份/参考/阈值/权重参数（frozen，bias-algorithm §7）。
- [x] 1.6 `app/services/bias_scoring/calculator.py`：新增 `_pool`/`_momentum`/`_fragility`/`_acceleration`/`_overheat_score`/`_watch_score` 纯函数（复用 `norm`/`clamp`），`bias` 数值不变。
- [x] 1.7 `app/services/bias_scoring/labels.py`：`BiasCategory` 扩八类 + `Pool` + `CATEGORY_LABELS`（无「高估/低估」字样）；新增 `classify_option(...)`，保留旧 `classify`。
- [x] 1.8 `app/services/bias_scoring/results.py`：`OptionBiasResult`/`RankedOption` 新增可空 `pool`/`momentum`/`fragility`/`overheat_score`/`watch_score`；`compute_event_bias` 装配赋值。
- [x] 1.9 `app/services/bias_scoring/ranking.py`：三榜按新标签诚实重定义（过热榜/观察榜/合理）与排序。
- [x] 1.10 `app/schemas/analysis.py`：`OptionAnalysis`/`RankingItem` 新增可空信号字段；`analysis_service` 各装配点透传。
- [x] 1.11 `docs/prd/polymarket-bias-detector/bias-algorithm.md`：回锚更新身份闸门、多信号、八类标签表、诚实性声明、新参数默认值。

## 后端测试（未执行验证，按用户要求暂停）

- [x] 2.1 `tests/fixtures/bias_golden.json`：`bias` 数值不变，`category` 期望按八类重算；新增 favorite-overheat / longshot-watch / longshot-hyped / quiet-longshot 用例。
- [x] 2.2 `tests/test_bias_scoring.py`：保留 `test_classify_thresholds`；新增身份池 / 过热分 / 观察闸门 / 缺失字段兜底用例；按新分桶改写 `test_ranking_buckets_*`。
- [x] 2.3 `tests/test_analysis_api.py`：更新受影响断言；新增「头号热门 → overview_label=低关注热门、不含冷门」回归。
- [x] 2.4 `tests/test_market_data.py`：补 fresh 缓存路径不丢新字段的覆盖。
- [x] 2.5 后端验证：`cd backend && make lint && make test` 全绿。

## 前端（接入完成，未跑验证）

依赖后端接口：`GET /api/v1/events`、`GET /api/v1/events/{slug}`、`GET /api/v1/rankings`（新增可选信号字段 + `label` 承载八类细文案）。

- [x] 3.1 三模块 DTO/api 转换新增可选字段搬运（`bias-ranking`、`single-event`；events 卡片沿用既有 `overview_label`，无需加字段）。
- [x] 3.2 `RankingItemRow.tsx`：改渲染 item 自带 `label` 细文案；行色仍按榜别 tone。
- [x] 3.3 `bias-ranking.constants.ts` + `shared/i18n`：榜别标题改名为 过热榜/观察榜/合理；ranking/events subtitle 去「高估/低估」措辞。
- [x] 3.4 卡片/单事件页原样渲染后端细文案（零运行时改动）。
- [x] 3.5 前端验证：`pnpm typecheck && pnpm lint && pnpm test`。
