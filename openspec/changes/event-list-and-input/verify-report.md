# Verify Report — event-list-and-input

## 2026-07-06 · apply 后 verify 门禁（qa + ui-ux-reviewer）

**结论：PASS（无 CRITICAL）**

验证命令：
- `openspec validate event-list-and-input --type change --strict`（仓库根）→ valid
- `cd frontend && pnpm typecheck` → 通过 · `pnpm lint` → 通过 · `pnpm test` → 20 passed

核对：18 项 tasks 均有实现证据；`events.api.ts` 经 `shared/api` 统一 client 调三接口（GET events / POST resolve / GET search），无组件内直发；分页 useInfiniteQuery + has_more；链接解析 vs 名称搜索分派；加载/空/错误/成功/搜索无结果/解析失败态齐全（复用 EmptyState/ErrorState）；卡片点击导航 `/events/:eventId`；类型对齐 snake_case 契约；route entry 仅 composition，UI 区块下沉 `pages/events/ui/`。AppRouter 仅改 `/events` 一条。

findings：
- **WARNING（待决 · product-manager）** — 契约缺口：analysis-api `overview_label`/option `label` 为本地化文案 `{zh,en}`，无 `category:'hot'|'cold'|'fair'` 枚举，`BiasLabel` 需 category 必填 prop，故卡片概览标签只能中性 token 呈现、失去偏差信号色（产品第一眼价值）。前端未越界在客户端重算阈值分类（处理正确）。建议上游契约补 `category` 枚举后接回 `BiasLabel`。
- **WARNING（frontend-dev）** — `EventInputPanel.module.css` disabled 主按钮借用 `--color-fair-core`（偏差 fair 信号色），跨语义借色，建议改中性 token（tokens.css 明示不要跨语义借色）。
- **SUGGESTION** — 裸 slug（无 polymarket.com/http 前缀）落名称搜索而非 resolve，属合理启发式，建议 product-manager 确认预期分派。
- **SUGGESTION** — EventCard chip `padding: 2px 10px` 为 off-scale 裸值，建议归并到 `--space-*` 刻度或新增控件内边距 token。
