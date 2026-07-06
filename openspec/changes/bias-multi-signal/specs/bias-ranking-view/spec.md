## ADDED Requirements

### Requirement: 三榜诚实重定义
`bias-ranking-view` SHALL 将三榜语义重定义为「过热榜 / 观察榜 / 合理」：过热榜收纳「过热热门 + 过热中位 + 被炒作冷门」并按 `overheat_score` 降序；观察榜收纳「观察冷门 + 低关注热门」并按 `watch_score` 或 `|crowding|` 排序；合理收纳「共识热门 + 中位竞争者 + 普通冷门」。榜别标题与文案 MUST NOT 含「高估/低估」字样。来源：PRD §4.4；bias-algorithm §5。

#### Scenario: 头号热门不进入冷门/观察外的错误榜
- **WHEN** 头号热门被标为「低关注热门」
- **THEN** 它出现在观察榜，且不出现在过热榜或合理榜的冷门位

### Requirement: 榜单项按各自细标签渲染
排行项 SHALL 渲染后端返回的各自八类细标签文案（而非仅按榜别注入统一文案）；行信号色可仍按榜别 tone。来源：PRD §4.4。

#### Scenario: 同榜不同细标签分别显示
- **WHEN** 观察榜同时含「观察冷门」与「低关注热门」两项
- **THEN** 两项分别显示各自细标签文案
