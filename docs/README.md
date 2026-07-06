# 文档中心（docs）

> 本仓库 **polyEdge** 是一个 monorepo：`frontend/`（Vite + React + TypeScript Web）与 `backend/`（FastAPI + PostgreSQL + SQLAlchemy 2.0 同步 + Pydantic v2 + Redis + JWT，Python ≥ 3.10，uv 管理）两个应用，共用根级 `docs/` 与根级协作入口 `CLAUDE.md`。
> 本文件是文档体系的入口与地图，只判断「该读哪个文档」，不堆全部内容。后端接口事实源是运行时 OpenAPI（`backend` 的 `/docs`）。
> Agent 工作流基础设施（`manager/`、`openspec/`、`repairs/`、`scripts/`、`.claude/{agents,skills,commands}/`、`.codex/skills/`）统一置于**仓库根**；从仓库根运行相关 skill，一份 `manager/plan.yaml` + `openspec/` 同时编排 `frontend/` 与 `backend/`。

## 目录职责

| 目录 | 作用 | 不放什么 |
|---|---|---|
| [`docs/frontend/`](./frontend/README.md) | 前端工程规范、组件维护说明、模板落地指南入口 | 业务 PRD、接口契约、当前执行状态 |
| `docs/frontend/architecture/` | 前端技术基线、架构边界、目录分层、依赖方向 | 临时实现计划、业务 PRD |
| `docs/frontend/standards/` | 前端编码、组件、文件、样式、UI 状态与可访问性规范 | 具体组件现状清单 |
| `docs/frontend/components/` | UI 组件治理指南、已落地组件清单、职责边界、复用判断 | 未落地设想、一次性设计稿 |
| `docs/frontend/guides/` | 基于模板创建新项目和已有项目迁入清单 | 长期架构规则 |
| [`docs/backend/`](./backend/architecture/technology-baseline.md) | 后端技术基线、`app/` 分层、依赖方向、数据流边界 | 业务 PRD、当前执行状态 |
| [`docs/backend/standards/`](./backend/standards/README.md) | 后端实现流程、日常编码、分层职责、文件组织、API/错误契约、基础设施（硬规则） | 具体业务需求、接口清单 |
| [`docs/ai/`](./ai/README.md) | agent 执行补充、Manager/OpenSpec 流程、上下文收集、交接格式、质量门禁 | 具体业务需求、接口契约、源码实现 |
| [`docs/api/`](./api/README.md) | 前后端联调的接口契约、OpenAPI 快照、mock、错误码说明入口 | 组件规范、业务需求全文 |
| [`docs/prd/`](./prd/README.md) | 本项目需求来源、PRD、用户路径、业务规则、验收标准与设计输入入口 | 代码实现细节、接口契约正文、当前执行状态 |
| `manager/` | Manager 当前计划、OpenSpec 批次编排与轻量 archive | 通用工程规范、真实业务长期归档 |
| `repairs/` | 小范围修复队列、repair runner 执行 list、用户验证与 repair archive | Manager/OpenSpec 需求批次 |

> 说明：`docs/` 只沉淀**长期稳定的工程规范与本项目业务文档**。前后端各自的临时实现计划、当前任务状态由 `manager/plan.yaml` 与各 change 的 `tasks.md` 承载，不写进 `docs/`。

## 读取顺序（前端任务）

- 先看 [`docs/frontend/README.md`](./frontend/README.md) 判断前端文档入口。
- 前端实现任务：先看 `docs/frontend/standards/README.md`，再看 `docs/frontend/standards/frontend-development.md`。
- 组件命名、拆分、复用/新增判断或清单维护：看 `docs/frontend/components/components.md`、`component-splitting.md`、`component-inventory.md`。
- 组件 props、可控/非可控、状态表达、数据边界：看 `docs/frontend/standards/component-definition.md`。
- 目录放置、页面私有组件、feature/entity/shared 划分或 hook 放置：看 `docs/frontend/standards/file-organization.md`。
- loading、empty、error、disabled、focus、键盘操作或可访问性：看 `docs/frontend/standards/accessibility-and-ui-states.md`。
- 技术选型、依赖方向、`src/` 分层或架构边界：看 `docs/frontend/architecture/technology-options.md`。
- 新项目创建或已有项目迁入模板规范：看 `docs/frontend/guides/project-bootstrap.md`。

## 读取顺序（后端任务）

1. 日常编码入口：[`docs/backend/standards/python-development.md`](./backend/standards/python-development.md)。
2. 新增资源域或从零加接口：按 [`docs/backend/standards/implementation-workflow.md`](./backend/standards/implementation-workflow.md) 的步骤清单（契约 → 表 → 数据访问 → 业务 → 路由 → 验证）执行。
3. 新代码放哪一层、模块命名：看 [`docs/backend/standards/file-organization.md`](./backend/standards/file-organization.md)。
4. 某层（api/service/repository/model/schema）怎么写、跨层边界：看 [`docs/backend/standards/layer-definition.md`](./backend/standards/layer-definition.md)。
5. 接口形状、响应结构、异常、状态码、鉴权：看 [`docs/backend/standards/api-and-error-contract.md`](./backend/standards/api-and-error-contract.md)。
6. 配置、事务、Redis、JWT、中间件：看 [`docs/backend/standards/infrastructure.md`](./backend/standards/infrastructure.md)。
7. 技术选型、依赖方向、`app/` 分层：看 [`docs/backend/architecture/technology-baseline.md`](./backend/architecture/technology-baseline.md)。

## 读取顺序（协作 / 业务）

- agent 工作方式、上下文收集、交接或验证口径：看 `docs/ai/agent-guide.md`。
- PRD 到 OpenSpec 批次规划、执行当前 Manager 批次、Goal 连续推进：看 `manager/plan.yaml`、`docs/ai/openspec-manager-flow.md` 和对应 `manager-*` skill。
- 一个需求该拆成几个 OpenSpec change、data-flow 是否单独建 change：看 `docs/ai/openspec-manager-flow.md#OpenSpec 拆分粒度`。
- 自然语言问题登记、小范围修复队列、用户验证后归档：看 `repairs/README.md`、`repairs/list.yaml`、`$repair-intake`、`$repair-runner`。
- 接口契约、mock、错误码或联调说明：看 [`docs/api/README.md`](./api/README.md)。
- PRD、用户路径、业务规则或验收标准：看 [`docs/prd/README.md`](./prd/README.md)。

## Shared Component Usage（前端）

- 写 UI 前先查项目是否已有可复用组件、样式 token、hook 或工具函数，优先复用现有实现。
- `button`、`input`、`select`、`dialog`、`popover`、`tooltip`、`menu`、`card`、`empty state`、`loading` 等基础 UI，不在业务代码里重复手写一套。
- 现有公共组件只缺少小能力时，优先在不破坏已有调用的前提下扩展它；不为同一类 UI 新建平行组件。
- 只有当前页面或当前业务场景使用的组件，先放在所属模块内部；不因为未来可能复用提前放入 `shared/ui`。

## 硬约束（跨前后端，不在细则里重复，但必须遵守）

- **后端统一响应**：所有接口经 `ApiResponse[T]` / `success_response(...)` 返回 `{code,message,data}`，不手拼 dict、不返回裸 ORM 对象。
- **后端统一异常**：业务错误只抛 `core/exceptions.BusinessException` 及子类，由全局 handler 转响应；不裸抛 `HTTPException`、不返回错误字典。
- **前端样式**：只用 `frontend/src/shared/styles/tokens.css` 的 token，不硬编码颜色 / 圆角 / 阴影。
- **前端请求**：一律经 `frontend/src/shared/api` 的统一 `requestClient`（axios），不在组件里直接发请求。
- **敏感信息**：只走 `.env` / 环境变量（后端 `core/config.Settings` 读取），永不硬编码、永不入库、永不进 Git。
- **表结构变更**：后端必须生成 Alembic 迁移并 `upgrade head` 验证。

## 维护规则

- 长期稳定规则写入 `docs/frontend/`、`docs/backend/` 或 `docs/ai/`；临时执行计划、当前任务状态不写进来。
- 每条具体规则只放一个 owner 文件，其他文件引用不复制。
- 具体业务内容写入 `docs/prd/`、`docs/api/`；文档示例保持业务中性，优先用 `ComponentName`、`feature-name`、`Entity`、`Resource` 等占位名。
- 新增、改名或删除规范文件时，同步更新本文件与对应目录的 `README.md` 文档地图。
