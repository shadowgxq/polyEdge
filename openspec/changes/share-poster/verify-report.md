# Verify Report — share-poster

## 2026-07-06 · apply 后 verify 门禁（qa + ui-ux-reviewer）

**结论：PASS（无 CRITICAL；ui-ux 初判 FAIL 的唯一硬约束违规已在本轮修复）**

验证命令：
- `openspec validate share-poster --type change --strict`（仓库根）→ valid
- `cd frontend && pnpm typecheck` → 通过 · `pnpm lint` → 通过 · `pnpm test` → 23 passed
- `frontend/package.json` 确含 `html-to-image@^1.11.13`（非臆造）

核对：22/22 tasks 有实现证据；图片代理 URL 拼装（`imageProxy.utils.ts`）改写为同源 `GET /api/v1/image-proxy?url=...`、走 `shared/api` 基址、组件不直连 Polymarket 域；出图（`posterCapture.ts`）`fonts.ready` + 图片 load/`decode` 后 `toBlob`、DPR≥2、失败 ErrorState+重试；分发能力探测/降级（Web Share/下载/复制/intent，AbortError 不计错误）；数据复用 single-event-detail/bias-ranking 展示源、不重算偏差；`features/share-poster/{model,ui}` 拆分合规、Radix Dialog 焦点管理与 i18n aria-label 齐全。

### 本轮修复（apply 内）
- **硬约束违规修复**：`SharePosterDialog.module.css` 遮罩 `rgba(30,32,40,0.45)` 硬编码颜色 → 在 `tokens.css` 新增 `--color-overlay` 语义 token 并引用；复验 typecheck/lint 通过，share-poster 目录无残留硬编码颜色。ui-ux 初判 FAIL 的唯一阻断项消除。

findings（剩余，均非阻断）：
- **WARNING（待决 · product-manager）** — 榜单海报缺「数据快照时间」：`RankingBoardsDto` 无 `data_snapshot_at`，榜单海报仅标注海报生成时间；单事件海报两时间齐全。属上游契约缺口。
- **WARNING（待决 · product-manager）** — 单事件海报核心选项因 option `label` 缺 category 枚举走中性文案兜底，未用 BiasLabel 信号色（榜单经榜别分组 category 合法，走 BiasLabel）。全站契约缺口。
- **SUGGESTION（frontend-dev）** — Web Share 入口探测偏粗（仅测 `navigator.share`/`canShare` 存在），桌面部分浏览器 `canShare({files})` 为 false 时按钮仍显示、点击落到下载引导（不静默，闭环无损）。
- **SUGGESTION（frontend-dev）** — 出图失败时「复制链接」与 intent 分享一并隐藏，二者本不依赖图片，可保留以在出图失败时仍有分享闭环。
