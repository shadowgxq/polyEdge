## ADDED Requirements

### Requirement: 从既有 events 响应映射白拿字段
`polymarket-client` 归一化 SHALL 从既有 Gamma `GET /events` 同一响应的 market 对象额外映射 `oneDayPriceChange`/`oneWeekPriceChange`/`bestBid`/`bestAsk`/`spread`/`volume1wk`/`volume1mo`/`competitive` 到对应 `MarketOption` 字段，MUST NOT 为此新增任何上游端点调用。来源：data-source §2、§3。

#### Scenario: 零新请求映射
- **WHEN** 拉取事件列表或单事件
- **THEN** 新字段来自同一 `/events` 响应，上游请求次数与升级前一致

#### Scenario: 字段缺失容错
- **WHEN** 响应中某 market 无 `spread` 或 `competitive`
- **THEN** 对应选项字段为 None，归一化不中断
