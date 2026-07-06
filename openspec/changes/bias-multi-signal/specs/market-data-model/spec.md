## ADDED Requirements

### Requirement: 选项级扩展信号字段
归一化选项模型 `MarketOption` SHALL 新增可空字段承载白拿信号：`one_day_price_change`、`one_week_price_change`、`best_bid`、`best_ask`、`spread`、`volume1wk`、`volume1mo`、`competitive`。字段缺失时置 None，诚实标缺失、不臆造。来源：data-source §2；bias-algorithm §3.2。

#### Scenario: 上游缺字段时置空
- **WHEN** 某市场响应未提供 `oneDayPriceChange` 或 `spread`
- **THEN** 对应字段为 None，不填默认值、不报错

#### Scenario: 新字段向后兼容旧快照
- **WHEN** 反序列化不含新字段的历史快照
- **THEN** 新字段取 None，模型校验通过
