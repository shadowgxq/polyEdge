## ADDED Requirements

### Requirement: 分层缓存承载扩展字段
Redis 分层缓存 SHALL 将新增波动量字段（`best_bid`/`best_ask`/`spread`/`one_day_price_change`）纳入短 TTL 价格层白名单，将慢变量字段（`one_week_price_change`/`volume1wk`/`volume1mo`/`competitive`）纳入长 TTL 元数据层白名单，并在事件重建（`_merge_event`）时一并还原。来源：data-source §缓存分层。

#### Scenario: fresh 读路径不丢新字段
- **WHEN** 写入含新字段的事件后经 fresh 缓存路径读取
- **THEN** 读回事件包含全部新增字段，值与写入一致

#### Scenario: fallback 快照兼容
- **WHEN** 走 fallback / DB 快照（`model_dump`）读回
- **THEN** 新字段随模型带出，无需 Alembic 迁移
