# Tasks

> 前端为主单端 change。出图与分发在前端完成。数据复用 `single-event-detail`（`EventDetail`/`OptionAnalysis`）与 `bias-ranking`（`RankingBoards`/`RankingItem`）已有展示数据源，不重算偏差。海报内 Polymarket 图片经后端图片代理同源加载（**依赖后端接口 图片代理（image-proxy）：`GET /api/v1/image-proxy?url=<原图URL>` → 二进制图片流**），本 change 只消费不实现。首次编辑前端代码前先读 docs/frontend/standards/frontend-development.md、components/components.md、components/component-splitting.md、standards/file-organization.md、standards/accessibility-and-ui-states.md。

## 前端

### 1. 依赖与出图 service

- [x] 1.1 将 `html-to-image` 加入 `frontend/package.json` 依赖（单库主选，不引第二出图库）；如无法安装在交付说明标注（spec：受控离屏海报出图；design D1）。
- [x] 1.2 新增出图 service：封装 `html-to-image` 调用，参数 `pixelRatio = max(devicePixelRatio, 2)`、内联字体、出图前 `await document.fonts.ready`；返回图片 Blob/DataURL；出图失败抛可捕获错误供上层降级（spec：受控离屏海报出图，PRD §4.5；design D1/D2）。
- [x] 1.3 新增图片代理 URL 拼装工具：把海报内 Polymarket 图片原始 URL 改写为同源 `GET /api/v1/image-proxy?url=<原图URL>`，走 `shared/api` 基址；组件不直连 Polymarket 图片域（spec：海报内 Polymarket 图片经代理同源加载，PRD §1.4；design D3）。**依赖后端接口 图片代理（image-proxy）**

### 2. 受控离屏海报卡片

- [x] 2.1 下沉受控离屏海报卡片组件（off-screen 挂载容器：移出视口/隐藏但可渲染），只含受控元素、内联字体，规避背景图/CSS 滤镜/icon-font（spec：受控离屏海报出图；design D2）。
- [x] 2.2 海报卡片内容：事件/榜单标题、核心选项与三分类 `BiasLabel`（复用外壳基元，按 `label{zh,en}` 取当前语言）、偏差评分、来源标注（Polymarket）；单事件「核心选项」取 `|bias|` 最大项，前端只挑选不重算（spec：海报卡片内容与时间区分展示，PRD §4.5、§4.1；design D6）。
- [x] 2.3 时间双标注：经 `SnapshotTime` 基元标注「数据快照时间」（`data_snapshot_at`），另标注「海报生成时间」（出图触发时刻），两字段独立、不混用（spec：海报卡片内容与时间区分展示，PRD §5.3；design D4）。
- [x] 2.4 海报内 Polymarket 图片用 1.3 的代理 URL 作 `src`，出图前确保图片加载/`decode` 完成再触发出图（spec：海报内 Polymarket 图片经代理同源加载；design D3）。**依赖后端接口 图片代理（image-proxy）**
- [x] 2.5 海报采用移动优先竖版尺寸，桌面复用竖版；超长英文事件名/选项名截断/换行；样式只用 `tokens.css` token（spec：移动优先竖版海报与窄屏适配，PRD §4.5、AC-9）。

### 3. 分发能力探测与分派

- [x] 3.1 新增分发能力探测工具：探测 `navigator.share` + `navigator.canShare?.({files})`（分享图片文件）、`navigator.clipboard.write` + `ClipboardItem`（复制图片，条件能力，需安全上下文）（spec：复制图片到剪贴板为条件能力、分享降级与失败态矩阵；design D5）。
- [x] 3.2 移动端 Web Share：支持分享文件时经 `navigator.share({files})` 分享海报图片文件到系统原生面板（spec：移动端 Web Share 图片文件分发，PRD §4.5、AC-6）。
- [x] 3.3 桌面端下载海报图片与复制链接入口，操作结果有明确反馈（spec：桌面端下载/复制链接/intent 分享）。
- [x] 3.4 桌面端 intent 分享 X / Telegram / Facebook / Reddit：各平台 share URL 拼 `window.open`，文案随语言经 i18n 插值、市场内容作变量注入（spec：桌面端下载/复制链接/intent 分享，PRD §4.5、§4.6）。
- [x] 3.5 条件能力「复制图片到剪贴板」：支持时暴露入口并写入剪贴板；不支持时自动隐藏并以下载回退（spec：复制图片到剪贴板为条件能力，PRD §4.5、AC-6；design D5）。

### 4. 入口挂载与状态编排

- [x] 4.1 在单事件明细结果处挂分享入口：触发时以 `EventDetail`/`OptionAnalysis` 展示数据编排出图 + 分发；入口键盘可达 + i18n 插值 `aria-label`；只读、无交易入口（spec：单事件与榜单分享入口，PRD §4.5、AC-6/AC-7）。
- [x] 4.2 在偏差排行某个榜单处挂分享入口：触发时以 `RankingBoards`/`RankingItem` 展示数据编排出图 + 分发（spec：单事件与榜单分享入口；design D6）。
- [x] 4.3 出图/分发编排下沉分享模块，route page 只做 composition；出图/分发为命令式动作，用本地组件态承载 loading/error，不引入 Query（design D7）。

### 5. 降级与失败态

- [x] 5.1 出图失败：呈现 `ErrorState` 基元 + 重试，可降级下载，不整页报错不静默（spec：分享降级与失败态矩阵，PRD §5.2、AC-5）。
- [x] 5.2 Web Share 缺失/不支持文件：退化为下载 + 复制链接；分享调用失败（非用户取消）呈现可重试错误态（spec：移动端 Web Share 图片文件分发、分享降级与失败态矩阵，AC-6）。
- [x] 5.3 各能力缺失按 3.1 探测隐藏对应入口并保留可用回退（Web Share 缺失→下载+复制链接；复制图片缺失→下载）（spec：分享降级与失败态矩阵；design D5）。

### 6. i18n 与验证

- [x] 6.1 新增分享相关 i18n key（en/zh）：分享入口、海报标题/来源/时间标签、intent 文案、各失败态；含市场内容句子用占位符插值 key，事件名/选项名作不翻译变量注入（spec：海报卡片内容与时间区分展示，PRD §4.6；design D8）。
- [x] 6.2 分享入口与失败态在 ≤430px 窄屏无横向滚动、无文本溢出，仅用 `tokens.css` 布局 token（spec：移动优先竖版海报与窄屏适配，AC-9）。
- [x] 6.3 在 `frontend/` 下运行 `pnpm typecheck` + `pnpm lint`（必要时 `pnpm test`）；如缺依赖/脚本/授权无法执行则在交付说明中标注。
