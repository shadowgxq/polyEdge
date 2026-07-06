## ADDED Requirements

### Requirement: 事件出参承载扩展信号与诚实标签
`analysis-event-api` 的单选项出参（`OptionAnalysis`）SHALL 新增可空字段 `pool`、`momentum`、`fragility`、`overheat_score`、`watch_score`；事件卡片概览标签（`overview_label`）与选项标签（`label`）SHALL 承载八类诚实标签的中/英文案。新增字段全部可选，向后兼容。来源：PRD §4.1/§4.3；bias-algorithm §4。

#### Scenario: 头号热门卡片显示低关注热门
- **WHEN** 事件内 |crowding| 最大选项属 FAVORITE 池且 crowding 为负
- **THEN** 卡片 `overview_label` 文案为「低关注热门」，不含任何「冷门」字样

#### Scenario: 新字段可选不破坏旧客户端
- **WHEN** 客户端忽略新增信号字段
- **THEN** 原有 `price`/`heat`/`bias_score`/`label` 字段结构不变，响应可正常解析
