## ADDED Requirements

### Requirement: 中英双语与默认语言

系统 SHALL 支持 English 与中文两种界面语言，默认语言 SHALL 为 English。本地化范围为本产品自身 UI 文案（导航/按钮/空态/错误提示、偏差三分类标签、榜单与分享措辞、数据完整度与时间标注）。系统 SHALL NOT 翻译市场内容（Polymarket 事件名、选项名按英文源文本原样展示）。来源：PRD §4.6、§5.4、AC-8。

#### Scenario: 默认以 English 渲染

- **WHEN** 访客在无既存语言偏好时首次进入
- **THEN** 界面 UI 文案以 English 渲染

#### Scenario: 市场内容不翻译

- **WHEN** 界面语言为中文且展示含市场内容的文案
- **THEN** UI 文案为中文
- **AND** 其中的事件名/选项名保持英文源文本，不被翻译

### Requirement: 语言切换与持久化

系统 SHALL 提供语言切换入口，切换后界面 UI 文案与偏差标签立即随所选语言更新。所选语言 SHALL 持久化到 `localStorage`，刷新后保持不丢失；语言属界面本地状态，不经服务端。来源：PRD §4.6、§5.4、AC-8。

#### Scenario: 切换语言即时生效

- **WHEN** 访客通过语言切换入口从 English 切到中文
- **THEN** 界面 UI 文案与偏差三分类标签更新为中文

#### Scenario: 刷新后保持所选语言

- **WHEN** 访客选择中文后刷新页面
- **THEN** 页面从 `localStorage` 读取偏好并以中文渲染

### Requirement: 市场内容插值 key 约定

凡含市场内容的句子（如「{eventName} 中 {optionName} 偏差最高」）系统 SHALL 使用带占位符的插值 key，事件名/选项名作为不翻译变量注入，SHALL NOT 与译文字符串拼接硬编码。来源：PRD §4.6、§5.4。

#### Scenario: 含市场内容句子用插值 key

- **WHEN** 渲染一条含事件名与选项名的句子
- **THEN** 译文来自带 `{eventName}`/`{optionName}` 占位符的插值 key
- **AND** 事件名/选项名作为变量注入，不参与翻译、不做字符串拼接

### Requirement: 偏差三分类标签中英文案

系统 SHALL 内置偏差三分类标签的中英两套文案：`bias_i ≥ +T` → 高热度·泡沫风险 / Overheated · Bubble Risk；`bias_i ≤ -T` → 低热度·冷门机会 / Underhyped · Value Opportunity；`-T < bias_i < +T` → 合理 / Fairly Priced。标签文案 SHALL 随当前语言切换，供列表/明细/排行/分享统一复用。来源：PRD §4.6、bias-algorithm §4。

#### Scenario: 三分类标签随语言呈现

- **WHEN** 当前语言为 English 且某选项分类为 hot（泡沫风险）
- **THEN** 标签文案呈现为「Overheated · Bubble Risk」

#### Scenario: 中文标签口径一致

- **WHEN** 当前语言为中文且某选项分类为 cold（冷门机会）
- **THEN** 标签文案呈现为「低热度·冷门机会」
