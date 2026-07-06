# CLAUDE.md

> 本文件是 **polyEdge**（Polymarket 热门-冷门偏差检测器）仓库的 AI agent 协作入口规则。任何任务开始前先读本文件并遵循。
> 项目结构：monorepo，`frontend/`（Vite + React + TypeScript Web）+ `backend/`（FastAPI + PostgreSQL + SQLAlchemy 2.0 同步 + Pydantic v2 + Redis + JWT，Python ≥ 3.10，uv）。工程规范单一事实源在根 `docs/`。
> Agent 工作流基础设施（`manager/`、`openspec/`、`repairs/`、`scripts/`、`.claude/{agents,skills,commands}/`、`.codex/skills/`）统一置于**仓库根**，从仓库根运行相关 skill；一份 `manager/plan.yaml` + `openspec/` 同时编排 `frontend/` 与 `backend/`。

## Communication

- 默认使用中文沟通和解释。
- 技术术语、命令、路径、文件名、环境变量、配置键、错误信息、日志和 URL 保持原文。

## Working Principles

- 优先理解用户目标、当前上下文、交互路径和数据流；不清楚时先查现有实现和文档，再动手。
- 仍有影响结果的歧义时先提一个简短问题；影响较小时自主判断并在交付时说明。
- 改动遵循最小范围原则，只处理当前任务直接相关的内容，不顺手重构、格式化或抽象无关代码。
- 复用既有分层与模式，不为单个功能新造平行目录结构。

## Documentation

- 文档目录职责与文档地图统一参考 [docs/README.md](docs/README.md)；进入具体规范前先经它分流，只按需读取和当前任务相关的细则。
- 在首次编辑文件前完成必要规范读取；任务范围扩大时再补读新增范围对应规范。
- **首次编辑前端代码前**至少先读 [docs/frontend/standards/frontend-development.md](docs/frontend/standards/frontend-development.md)。
- **首次编辑后端代码前**至少先读 [docs/backend/standards/python-development.md](docs/backend/standards/python-development.md)。

## Frontend Implementation（改动 `frontend/` 时）

- 新增需求、新增页面或扩展既有功能时，按实际涉及范围读取 [docs/frontend/README.md](docs/frontend/README.md) 分流到 `architecture/`、`standards/`、`components/` 或 `guides/` 后执行。
- 涉及 UI、组件、表单、列表、详情、交互状态或组件拆分时，追加读取 `docs/frontend/components/components.md`、`docs/frontend/components/component-splitting.md` 和 `docs/frontend/standards/file-organization.md`。
- route page entry 只承担路由参数、页面级 composition、状态归属和数据流编排；独立 UI 区块下沉为命名组件。
- 硬约束：样式只用 `frontend/src/shared/styles/tokens.css` 的 token，不硬编码颜色/圆角/阴影；网络请求一律经 `frontend/src/shared/api` 的统一 `requestClient`（axios），不在组件里直接发请求。

## Backend Implementation（改动 `backend/` 时）

- 新增资源域或从零加接口，按 [docs/backend/standards/implementation-workflow.md](docs/backend/standards/implementation-workflow.md) 的步骤清单（契约 → 表 → 数据访问 → 业务 → 路由 → 验证）执行。
- 涉及新代码放哪一层、模块命名，看 [docs/backend/standards/file-organization.md](docs/backend/standards/file-organization.md)；某一层怎么写、跨层边界，看 [docs/backend/standards/layer-definition.md](docs/backend/standards/layer-definition.md)。
- 涉及响应结构、异常、状态码、鉴权，看 [docs/backend/standards/api-and-error-contract.md](docs/backend/standards/api-and-error-contract.md)；涉及配置、事务、Redis、JWT、请求日志中间件，看 [docs/backend/standards/infrastructure.md](docs/backend/standards/infrastructure.md)。
- 硬约束：
  - 依赖只向下 `api → services → repositories → models`；横切 `schemas` / `core` 被各层依赖但不反向依赖业务层。
  - 统一响应只走 `ApiResponse[T]` / `success_response(...)`；业务错误只抛 `core/exceptions.BusinessException` 及子类，由全局 handler 转响应，不裸抛 `HTTPException`、不返回错误字典。
  - 敏感信息（`SECRET_KEY`、DB 密码）只走 `.env` / 环境变量（`core/config.Settings` 读取），永不硬编码、永不入库、永不进 Git。

## Constraints

- 开发阶段只做最小必要检查，不主动执行 `dev server`、`build`、`deploy`、`publish` 等高副作用命令。
- 未经用户明确要求，不执行 `git add`、`git commit`、`git push`。
- 不修改、回滚、覆盖或提交与当前任务无关的文件，尤其是 dirty worktree 中已有的用户改动。
- 改表结构必须生成 Alembic 迁移，不手改表不留记录。

## Delivery

- 交付时说明本次修改范围，以及已执行 / 未执行的验证。
- 前端改动验证：在 `frontend/` 下 `pnpm typecheck` + `pnpm lint`（必要时 `pnpm test`）。
- 后端改动验证：在 `backend/` 下 `make lint`（ruff）+ `make test`（pytest）；模型改动追加 `make migrate` + `make upgrade`。
- 如果验证因缺少依赖、脚本或用户授权无法执行，必须明确说明。
