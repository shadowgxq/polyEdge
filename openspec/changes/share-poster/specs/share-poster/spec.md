## ADDED Requirements

### Requirement: 单事件与榜单分享入口

系统 SHALL 在单事件明细结果与某个榜单两处提供分享入口，触发时对当前展示结果发起受控离屏海报出图与分发。分享入口 SHALL 键盘可达并带 i18n 插值的可读 `aria-label`（含事件/榜单名，作为不翻译变量注入，不字符串拼接）；全流程只读，MUST NOT 提供任何交易/下单/钱包连接入口。分享 SHALL 复用 `single-event-detail` 的单事件展示数据（`EventDetail`/`OptionAnalysis`）与 `bias-ranking` 的榜单展示数据（`RankingBoards`/`RankingItem`），SHALL NOT 在前端重算 `bias_i` 或阈值。来源：PRD §4.5、AC-6、AC-7、bias-algorithm §4。

#### Scenario: 单事件结果触发分享

- **WHEN** 访客在单事件明细对某可分析事件触发分享入口
- **THEN** 系统以该事件已算好的展示数据（标题、核心选项、偏差评分与三分类标签、数据快照时间）发起受控离屏海报出图，不重算偏差

#### Scenario: 榜单触发分享

- **WHEN** 访客在偏差排行对某个榜单触发分享入口
- **THEN** 系统以该榜单已算好的展示数据（榜单标题、榜单项的事件/选项/偏差评分与标签、数据快照时间）发起受控离屏海报出图，不重算偏差

#### Scenario: 分享入口键盘可达且只读

- **WHEN** 分享入口获得键盘焦点
- **THEN** 该入口可用键盘触发，其 `aria-label` 以 i18n 插值呈现，且页面不出现任何交易/下单/钱包连接入口

### Requirement: 受控离屏海报出图

系统 SHALL 通过前端将 DOM 渲染为图片，主选单库 `html-to-image`；出图 SHALL 为**受控离屏（off-screen）子集**渲染——只纳入受控卡片元素，**内联字体**，避免背景图 / CSS 滤镜 / icon-font 等易致导出空白的元素；SHALL 按 `devicePixelRatio`（≥2）高清渲染；出图前 SHALL 等待 `document.fonts.ready`。海报内 Polymarket 图片 SHALL 经后端图片代理（`image-proxy`）**同源加载**以规避 canvas 跨域污染。出图失败 SHALL 直接降级为下载/重试，MUST NOT 追求多库像素对齐兜底、MUST NOT 静默失败。样式 SHALL 仅用 `tokens.css` 的 token。来源：PRD §4.5、§1.4、AC-6。

#### Scenario: 高清受控离屏出图

- **WHEN** 系统对受控离屏海报子集出图
- **THEN** 使用 `html-to-image` 以 `devicePixelRatio`（≥2）渲染，内联字体，且在 `document.fonts.ready` 完成后才生成图片

#### Scenario: 海报内 Polymarket 图片经代理同源加载

- **WHEN** 海报卡片需要展示 Polymarket 图片
- **THEN** 该图片经后端图片代理以同源方式加载后再绘入 canvas，不因跨域污染导致导出失败

#### Scenario: 出图失败可重试不静默

- **WHEN** 出图过程失败
- **THEN** 系统呈现明确错误态（复用 `ErrorState`）并提供重试，同时可降级为下载，不静默失败

### Requirement: 海报卡片内容与时间区分展示

系统生成的海报卡片 SHALL 包含：事件/榜单标题、核心选项与其三分类偏差标签（复用 `BiasLabel` 基元）、偏差评分、来源标注（Polymarket），并 SHALL **区分展示**「数据快照时间」（Polymarket 数据获取时间 `data_snapshot_at`，经 `SnapshotTime` 基元）与「海报生成时间」（出图时刻），二者 MUST NOT 混用。海报文案 SHALL 跟随当前界面语言（中/英），市场内容（事件名/选项名）SHALL 保持英文源文本不翻译，含市场内容的句子 SHALL 用带占位符的插值 key。来源：PRD §4.5、§5.3、§4.6、AC-6、AC-8。

#### Scenario: 卡片含核心要素与来源

- **WHEN** 海报卡片渲染完成
- **THEN** 卡片呈现事件/榜单标题、核心选项与其偏差标签、偏差评分与 Polymarket 来源标注

#### Scenario: 数据快照时间与海报生成时间区分展示

- **WHEN** 海报卡片渲染时间标注
- **THEN** 卡片分别标注「数据快照时间」（`data_snapshot_at`）与「海报生成时间」（出图时刻），二者可区分、不混用

#### Scenario: 文案随语言且市场内容不翻译

- **WHEN** 当前界面语言为中文
- **THEN** 海报 UI 文案与偏差标签以中文呈现，事件名/选项名保持英文源文本，含市场内容的句子经插值 key 注入变量而非字符串拼接

### Requirement: 移动端 Web Share 图片文件分发

系统 SHALL 在支持 Web Share API 且支持分享文件的环境下，将出图结果作为**图片文件**经 Web Share API 分享到系统原生分享面板，供用户直达已安装的社媒/通讯应用。当环境不支持 Web Share API 或不支持分享文件时，系统 SHALL 退化为下载 + 复制链接，MUST NOT 静默失败。来源：PRD §4.5、AC-6、§5.2、AC-5。

#### Scenario: 支持时经原生面板分享图片

- **WHEN** 移动端环境支持 Web Share API 且支持分享文件
- **THEN** 系统调用 Web Share API 将海报图片文件分享到系统原生面板

#### Scenario: 不支持时退化为下载加复制链接

- **WHEN** 环境不支持 Web Share API 或不支持分享文件
- **THEN** 系统退化提供下载海报与复制链接入口，不呈现分享失败的空白态

#### Scenario: 分享失败呈现可重试错误态

- **WHEN** Web Share 调用过程失败（非用户主动取消）
- **THEN** 系统呈现明确错误态并提供重试，不静默失败

### Requirement: 桌面端下载/复制链接/intent 分享

系统 SHALL 在桌面端提供下载海报图片、复制链接，以及经 intent 分享到 X / Telegram / Facebook / Reddit（分享文案 + 链接）的入口。intent 分享文案 SHALL 跟随当前界面语言，其中市场内容作为不翻译变量注入。各入口 SHALL 键盘可达并带可读 `aria-label`。来源：PRD §4.5、AC-6、§4.6。

#### Scenario: 桌面下载与复制链接

- **WHEN** 访客在桌面端对某海报触发下载或复制链接
- **THEN** 系统分别提供海报图片下载与链接复制，操作结果有明确反馈

#### Scenario: intent 分享到四平台

- **WHEN** 访客在桌面端选择分享到 X / Telegram / Facebook / Reddit
- **THEN** 系统按对应平台的 intent 打开分享（携带随当前语言的文案与链接，市场内容作为变量注入）

### Requirement: 复制图片到剪贴板为条件能力

系统 SHALL 将「复制图片到剪贴板」作为**条件能力**：仅在支持的浏览器（安全上下文，Chromium 系较完整）暴露该入口；当环境不支持时，该入口 SHALL **自动隐藏并回退为下载**，MUST NOT 呈现不可用的入口或静默失败。来源：PRD §4.5、AC-6。

#### Scenario: 支持时可复制图片到剪贴板

- **WHEN** 浏览器处于安全上下文且支持复制图片到剪贴板
- **THEN** 系统暴露「复制图片」入口，触发后将海报图片写入剪贴板

#### Scenario: 不支持时隐藏并回退下载

- **WHEN** 浏览器不支持复制图片到剪贴板
- **THEN** 「复制图片」入口自动隐藏，系统以下载入口作为回退

### Requirement: 分享降级与失败态矩阵

系统 SHALL 分离处理分享全流程的降级与失败态，MUST NOT 静默失败：出图失败呈现错误态并可重试（复用 `ErrorState`）；分发能力缺失时按能力探测隐藏对应入口并保留可用回退（Web Share 缺失 → 下载 + 复制链接；复制图片缺失 → 下载）；分享调用失败（非用户取消）呈现可重试错误态。所有状态文案 SHALL 经 i18n。来源：PRD §5.2、AC-5、AC-6。

#### Scenario: 出图失败呈现错误态与重试

- **WHEN** 海报出图失败
- **THEN** 系统呈现本地化错误说明与重试入口，不整页报错、不静默失败

#### Scenario: 能力缺失按探测回退

- **WHEN** 当前环境缺失 Web Share 或复制图片能力
- **THEN** 系统隐藏对应入口并暴露可用回退（下载 / 复制链接），用户仍可完成分享闭环

### Requirement: 移动优先竖版海报与窄屏适配

系统 SHALL 提供适配移动端的**竖版**海报尺寸（移动优先）；MVP 桌面复用竖版，桌面横版列为后续增强。分享入口与失败态 SHALL 在 ≤430px 窄屏无横向滚动、无文本溢出，超长英文事件名/选项名按截断/换行/省略处理。布局 SHALL 仅使用 `tokens.css` 的 token。来源：PRD §4.5、AC-9。

#### Scenario: 竖版海报适配移动端

- **WHEN** 移动端生成分享海报
- **THEN** 海报以竖版尺寸出图，卡片内超长事件名/选项名按截断/换行呈现，不溢出

#### Scenario: 窄屏分享入口无横向溢出

- **WHEN** 视口宽度为 430px 或更窄
- **THEN** 分享入口与失败态无横向滚动、无文本溢出
