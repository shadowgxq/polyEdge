## ADDED Requirements

### Requirement: 对接 Gamma 与 CLOB 双 API 拉取归一

系统 SHALL 提供 Polymarket 客户端，对接 Gamma API（事件/市场/成交量/流动性/24h 成交量/评论数元数据）与 CLOB API（选项价格/隐含概率），将拉取结果归一到 `market-data-model` 契约。来源：PRD §1.4、data-source §1、bias-algorithm §2。

#### Scenario: 按 slug 拉取单事件

- **WHEN** 客户端收到一个事件 slug
- **THEN** 客户端从 Gamma 拉取该事件元数据、从 CLOB 拉取各选项价格，归一为一个内部事件模型（含选项集合、commentCount、数据快照时间）

#### Scenario: 元数据与价格双源合并

- **WHEN** 归一化某事件的选项
- **THEN** 选项的成交量/流动性/24h 成交量来自 Gamma、价格来自 CLOB（不可得时回退 outcomePrices），合并到同一选项模型

### Requirement: 默认列表与世界杯子集拉取

系统 SHALL 支持按热门规则（成交量/流动性等）拉取默认事件列表，并支持按体育/足球/World Cup 标签或关键词过滤出世界杯子集（同一数据源、仅筛选）。来源：PRD §4.1、data-source §1/§3。

#### Scenario: 拉取热门默认列表

- **WHEN** 客户端按热门规则请求默认事件列表
- **THEN** 返回一批按成交量/流动性等排序的事件，数量不超过配置的单次批量上限

#### Scenario: 世界杯子集为筛选结果

- **WHEN** 客户端请求世界杯事件子集
- **THEN** 在 Polymarket 事件中按世界杯标签/关键词过滤返回，不引入任何第三方数据源

### Requirement: 只读访问约束

系统 SHALL 对 Polymarket 仅执行只读拉取，MUST NOT 发起任何下单、钱包连接或资金操作请求。来源：PRD §1.3、data-source §5。

#### Scenario: 仅发只读请求

- **WHEN** 客户端与 Polymarket 交互
- **THEN** 只发起公开市场数据的读取请求，不触达任何交易/写入 endpoint

### Requirement: 上游指数退避重试

系统 SHALL 对 Polymarket 双 API 的请求在触发上游限流或瞬时失败时采用**指数退避重试**，退避参数（基础间隔、最大重试次数、上限）经配置读取，以避免放大对上游的请求压力。来源：PRD §5.2、data-source §5。

#### Scenario: 上游限流触发退避重试

- **WHEN** Polymarket 返回限流（如 429）或可重试的瞬时错误
- **THEN** 客户端按指数退避间隔重试，直到成功或达到最大重试次数后抛出上游失败

#### Scenario: 达到重试上限后上抛失败

- **WHEN** 重试达到配置的最大次数仍未成功
- **THEN** 客户端抛出上游拉取失败，交由缓存降级层处理，不静默返回空数据
