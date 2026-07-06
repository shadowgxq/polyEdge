## ADDED Requirements

### Requirement: 归一化事件/选项数据契约

系统 SHALL 定义一份内部归一化的事件/选项数据模型，作为 `bias-algorithm` 与 `analysis-api` 共享的市场数据契约。每个选项 MUST 承载 `price`（隐含概率，0~1）、`volume`、`liquidity`、`volume24hr`、`traders`（per-option 参与/持仓人数，可空）字段；每个事件 MUST 承载 `commentCount`（事件级）与其选项集合，字段口径对齐 data-source §2 与 bias-algorithm §2。来源：PRD §1.4、data-source §2、bias-algorithm §2。

#### Scenario: Polymarket 字段映射到内部选项模型

- **WHEN** 从 Polymarket 拉取到某事件的原始市场/选项数据
- **THEN** 系统将其映射为内部选项模型，填充 `price / volume / liquidity / volume24hr / traders`，并将事件级 `commentCount` 挂在事件模型上、不下放到单个选项

#### Scenario: commentCount 保持事件级

- **WHEN** 归一化一个含多个选项的事件
- **THEN** `commentCount` 仅作为事件级字段存在，不参与任何单选项字段，供下游作事件级关注度标签

### Requirement: 价格主源与退化回退

系统 SHALL 以 CLOB midpoint / best bid-ask 作为选项价格的主取价源；当 CLOB 价格不可得时 MUST 回退到 Gamma 的 `outcomePrices`，并在数据模型标注实际所用价源。来源：data-source §2、bias-algorithm §3.1。

#### Scenario: 主源可得时取 CLOB

- **WHEN** 某选项 CLOB midpoint 价格可得
- **THEN** 系统以 CLOB 价格作为该选项 `price`，并标注价源为 CLOB

#### Scenario: 主源不可得时回退 outcomePrices

- **WHEN** 某选项 CLOB 价格不可得但 Gamma `outcomePrices` 可得
- **THEN** 系统以 `outcomePrices` 作为该选项 `price`，并标注价源为退化回退

### Requirement: 二元与多 outcome 市场的粒度处理

系统 SHALL 区分两种事件结构归一到选项级：二元市场（market ≈ 单选项）字段直接作为选项级取数；多 outcome market 且 `volume / liquidity / volume24hr` 仅有 market 级、无法拆到选项级时，MUST 将该分量按缺失处理并在数据模型标注口径限制，不臆造选项级值。来源：data-source §2、bias-algorithm §3.1。

#### Scenario: 二元市场直接取选项级

- **WHEN** 归一化一个二元市场（market 即选项）
- **THEN** `volume / liquidity / volume24hr` 直接作为该选项级取数

#### Scenario: 多 outcome 无法拆分时按缺失处理

- **WHEN** 多 outcome market 的成交量/流动性字段仅有 market 级、无法拆到 outcome 级
- **THEN** 系统将该选项对应分量标为缺失并标注口径限制，交由下游按缺失兜底，不平均或估算填充

### Requirement: 无 per-option 参与数据判定谓词

系统 SHALL 提供「无 per-option 参与数据」的判定谓词：选项的 `traders`/`holders` 字段**缺失或为 `null`** MUST 判定为「无」（供下游触发退化）；字段值为 `0` MUST 判定为有效 0（正常参与、不触发退化）。来源：PRD §5.2、data-source §2、bias-algorithm §3.5。

#### Scenario: 缺失或 null 判为无

- **WHEN** 选项的 `traders` 字段缺失或为 `null`
- **THEN** 判定谓词返回「无参与数据」，供下游触发全事件退化

#### Scenario: 值为 0 判为有效

- **WHEN** 选项的 `traders` 字段值为 `0`
- **THEN** 判定谓词返回「有参与数据（有效 0）」，不触发退化

### Requirement: 数据快照时间

系统 SHALL 在每个归一化事件/选项数据结果上附带**数据快照时间**（Polymarket 数据获取时间），供下游展示与缓存一致性标注。来源：PRD §5.3、data-source §4。

#### Scenario: 归一化结果带快照时间

- **WHEN** 系统产出一份归一化事件数据
- **THEN** 该数据附带明确的数据快照时间字段，标识该快照的获取时刻
