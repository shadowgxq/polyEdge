# Verify Report — single-event-detail

## 2026-07-06 · apply 后 verify 门禁（qa + ui-ux-reviewer）

**结论：PASS（无 CRITICAL）**

验证命令：
- `openspec validate single-event-detail --type change --strict`（仓库根）→ valid
- `cd frontend && pnpm typecheck` → 通过 · `pnpm lint` → 通过

核对：13/14 tasks 有实现证据；`single-event.api.ts` 经 `shared/api` 调 `GET /api/v1/events/{slug}`（slug 缺失 enabled:false 不发请求）；出参对齐 `EventDetail`/`OptionAnalysis`；`/events/:eventId` route page 读 slug、加载/空/错误/成功四态分派、只读、面包屑返回；事件级降级（degraded_trade_only）/不适用（applicable=false）标注、选项「已排除」置底不参与排序；纯数值 bias_score 排序。route entry 仅 composition，UI 区块下沉。无需改 AppRouter（占位即 SingleEventPage 原地填充）。

findings：
- **WARNING（待决 · product-manager）** — task 3.3（hot/cold/fair 信号色区分，AC-3）未勾选：`OptionAnalysis.label` 为 `{zh,en}` 文案无 category 枚举，与 `BiasLabel`/`OptionMetricsRow` 必填 category 契约冲突，故三分类信号色无法达成。前端未越界重算分类（处理正确）。属跨 change 契约缺口，需上游 analysis-api 补 category 枚举。
- **WARNING（frontend-dev）** — task 3.1 已勾选但实现用页面私有 `EventOptionRow` 自绘指标行，未走共享 `OptionMetricsRow`/`BiasLabel`（同一 category 缺口根因）；四要素功能满足，但「经共享基元」表述与实现不符，建议随契约修复回归收敛。
- **WARNING（frontend-dev）** — 返回按钮仅 `navigate(-1)`，深链直达/刷新无应用内历史时可能跳出站；面包屑 `Link to="/events"` 已兜底，建议 back 加 history 守卫降级为 `/events`。
- **SUGGESTION** — `EventOptionRow` 指标结构与 `OptionMetricsRow` 高度重复，待 category 补齐后收敛回基元。
