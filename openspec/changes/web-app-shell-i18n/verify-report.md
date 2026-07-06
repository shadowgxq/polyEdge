# Verify Report — web-app-shell-i18n

## 2026-07-06 · apply 后 verify 门禁（qa + ui-ux-reviewer）

**结论：PASS（无 CRITICAL）**

验证命令：
- `openspec validate web-app-shell-i18n --type change --strict` → valid
- `cd frontend && pnpm typecheck` → 通过
- `cd frontend && pnpm lint` → 通过
- `cd frontend && pnpm test` → 9 文件 / 14 用例全过

### qa 核对
i18n 无偏好默认 English 且切换持久化、两 Tab 外壳与路由（`/`→`/events`、`/events`、`/events/:eventId`、`/ranking`、榜单回跳、面包屑返回）、共享基元（BiasLabel/OptionMetricsRow/SnapshotTime/EmptyState/ErrorState）、数据层 types.ts 与后端信封对齐、硬约束（token-only 样式、无组件内直连请求、route entry 仅 composition）均满足。tasks 27 项勾选均有证据。

qa findings：
- **SUGGESTION** — 面包屑 `<nav aria-label>` 复用 `detail.breadcrumbEvents`，a11y 宜用独立 Breadcrumb 标签。
- **SUGGESTION** — design 承诺的「无偏好 + navigator=zh 默认 en」用例未实测（代码路径正确，jsdom 默认 en-US 未走该分支）。
- **SUGGESTION** — `metrics.odds` / `bias.score` 为未引用预留 key，宜标注或清理。

### ui-ux-reviewer UI 走查 findings
- **WARNING** — off-scale 硬编码间距：新增 `--space-*` 阶梯（4/8/12/16/24/32）后，多处 padding/gap 用裸值（AppShell `6px 14px`、BiasLabel `2px 10px`、ErrorState `8px 16px`、LanguageSwitcher、gap `2px` 等）绕过间距 token。颜色/圆角/阴影零硬编码。建议归一到阶梯或补更细粒度控件内边距 token。
- **SUGGESTION** — `--breakpoint-mobile: 430px` 定义但无 media query 引用，宜注释为下游断点事实源。
- **SUGGESTION** — 明细返回 `navigate(-1)` 深链直达/刷新可能跳出站；面包屑 `Link to="/events"` 已兜底，建议下游 back 降级为 `/events` fallback。
- **SUGGESTION** — EmptyState `title` 必填、未回落 `empty.*`，与 ErrorState 缺省回落不对称。

无 CRITICAL；AC-9 窄屏无横向溢出为占位骨架的静态推断，未起 dev server 像素级验证。
