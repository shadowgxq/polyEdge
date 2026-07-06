## ADDED Requirements

### Requirement: 榜单项承载扩展信号与细标签
`analysis-ranking-api` 的榜单项（`RankingItem`）SHALL 新增可空字段 `pool`、`momentum`、`fragility`、`overheat_score`、`watch_score`，且 `label` SHALL 承载该选项八类诚实标签的中/英文案（不再仅作备用）。来源：PRD §4.4；bias-algorithm §5。

#### Scenario: 榜单项返回细标签
- **WHEN** 请求排行榜单
- **THEN** 每个榜单项的 `label` 为其八类细标签文案，可供前端直接渲染
