# Verify Report — bias-ranking

## 2026-07-06 · apply 后 verify 门禁（qa + ui-ux-reviewer）

**结论：PASS（无 CRITICAL）**

验证命令：
- `openspec validate bias-ranking --type change --strict`（仓库根）→ valid
- `cd frontend && pnpm typecheck` → 通过 · `pnpm lint` → 通过 · `pnpm test` → 20 passed

核对：12/12 tasks 有实现证据；`bias-ranking.api.ts` 经 `shared/api` `requestClient` 调 `GET /api/v1/rankings` 解包 `ApiResponse.data`（top_n 不传用后端默认）；三榜（bubble/underhyped/fair）展示、各榜空态 EmptyState；类型对齐 snake_case；宽屏三列 grid / ≤430px 分段 Tab 纵向、min-width:0 + overflow-wrap 无横向溢出；榜单项整行 Link 回跳 `/events/:eventSlug`（aria-label 插值可达）；route entry 仅 composition。**category 来源合法**：以后端已分好组的榜别（bubble→hot/underhyped→cold/fair→fair）驱动 BiasLabel 信号色，非客户端阈值重算，符合 spec「SHALL NOT 前端重算偏差/分类」。改动 `App.test.tsx`（移除被取代的占位样例链接，升级为排行→回跳集成测试）为本 change 直接后果，未破坏无关断言。样式全 token 无 off-scale 裸值。

findings：
- **SUGGESTION** — tasks 文案命名（`pages/ranking/`、`ranking.*`、`components/`）与实现（`pages/bias-ranking/`、`bias-ranking.*`、`ui/`）字面不符；实现遵循仓库既有约定与外壳预留模块，功能等价、非平行目录，建议对齐 tasks 文案。
- **SUGGESTION** — 榜标题可加极轻信号强调增强一眼扫读（fair 保持最低调）；loading 态可换骨架占位（design D6，当前纯文本已满足 spec）。
