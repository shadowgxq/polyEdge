## Context

分享海报由前端 DOM 出图（PRD §4.5），海报内需绘制 Polymarket 图片。跨域图片直接绘入 canvas 会污染画布导致 `toDataURL` / 导出失败，故需后端提供**同源图片代理**（PRD §1.4）。后端为 FastAPI，已具备 `httpx>=0.28.1` 依赖、`app/core/config.py`（Pydantic `Settings`）与 `app/core/exceptions.py`（`BusinessException` 体系）。代理直连任意 URL 是典型 SSRF / 开放代理面，data-source §3 明确了一组安全约束，本设计以该节口径为准，不自行放宽。

现状：`app/api/v1/` 下仅有 `auth.py`，无图片代理资源域；`Settings` 无图片代理相关配置。

## Goals / Non-Goals

**Goals:**
- 提供单一后端图片代理路由，同源返回 Polymarket 图片二进制流，供海报出图消费。
- 逐条落地 data-source §3 的 SSRF 安全约束：白名单 / 仅 https / 仅 image-* / 大小上限 / 超时 / 禁跨域重定向。
- 安全参数（白名单域、大小上限、超时）走 `core/config.Settings`，可通过 `.env` 调整，不硬编码。
- 错误路径统一走 `BusinessException` + 全局 handler；成功路径为二进制流。

**Non-Goals:**
- 前端海报出图、Web Share / 下载 / 复制 / intent 分发（属 share-poster change）。
- Polymarket 业务数据（事件 / 选项 / 偏差）拉取与缓存。
- 图片缓存 / CDN / 转码 / 压缩；本期仅做安全直转发。
- 放宽 data-source §3 任一约束（如允许 http、允许非白名单跳转）。

## Decisions

- **分层落点**：新增 `image-proxy` 资源域，`api` 层路由 + `services` 层做安全校验与出站拉取。依赖只向下 `api → services`；配置经 `core/config`，异常经 `core/exceptions`。不引入 repositories / models（无持久化）。相比把逻辑塞进路由函数，下沉到 service 便于对每条安全约束单测。
- **出站客户端**：复用已有 `httpx`。关键点是**关闭自动重定向**（`follow_redirects=False`），手动处理 3xx，以便对重定向目标复用全套白名单 / 协议校验（data-source §3 禁止跨域重定向）。选 httpx 而非 `requests`：已在依赖内、支持流式 `stream()` 与显式超时。
- **校验顺序（发请求前尽量拦截）**：解析目标 URL → 协议必须 `https` → host 必须命中白名单 → 再发起出站请求。前置校验避免对非法目标产生任何出站连接（防 SSRF 探测）。
- **白名单口径**：以**精确域名 / 后缀域**匹配 host（配置为域名列表），不使用正则宽匹配，避免 `evil-polymarket.com`、`polymarket.com.attacker.com` 之类绕过。白名单值来自 `Settings`（`.env`），默认仅 Polymarket 图片域。
- **内容类型校验**：收到响应后先读 `Content-Type`，仅 `image/*` 放行，否则中止并抛异常，不回传响应体（data-source §3）。
- **大小上限**：双重保护——若上游声明 `Content-Length` 超限直接拒绝；同时**流式**读取并累加字节数，超过 `Settings` 上限即中止，覆盖上游不声明 / 谎报长度的情况（data-source §3）。
- **超时**：`httpx` 显式 timeout 取自 `Settings`，覆盖 connect / read（data-source §3）。
- **重定向处理**：`follow_redirects=False`，遇 3xx 取 `Location`，对其重新跑「https + 白名单」校验；命中则以受控方式对新目标再拉取一次（限定跳转次数上限，防重定向环），否则抛异常（data-source §3 禁跨域重定向）。
- **响应形态**：成功返回 `fastapi.responses.StreamingResponse`（或等价二进制响应），`media_type` 用上游校验通过的 `image/*`；不包 `ApiResponse`。错误抛 `BusinessException` 子类（新增如 `ImageProxyInvalidTargetException` / `ImageProxyUpstreamException`），由全局 handler 统一转错误响应。
- **入参**：目标图片 URL 作为查询参数传入；空 / 缺失即拒绝，不发出站请求。

## Risks / Trade-offs

- [DNS rebinding：host 命中白名单但解析到内网 IP] → 本期以域名白名单 + 仅 https + 禁跨域重定向为主要防线（data-source §3 口径）；如需更强隔离，可在技术方案阶段追加对解析 IP 的私网段拒绝，作为白名单外增强，不放宽既有约束。
- [上游大图导致内存 / 带宽压力] → 流式读取 + 大小上限 + 超时三重限制；不落盘、不缓存。
- [重定向链绕过白名单] → 关闭自动重定向、逐跳复检、限定跳转次数上限。
- [白名单配置过窄导致合法图片被拒] → 白名单走 `.env` 可运维调整；默认覆盖 Polymarket 已知图片域，异常时前端有明确失败态（AC-6）。
- [代理被当作开放代理滥用] → 仅 `image/*` + 白名单 + 仅 https，非图片 / 非白名单一律拒绝，限制滥用面。

## Migration Plan

- 纯新增：新增 `image-proxy` 路由与 service、`Settings` 新增配置项、`core/exceptions` 新增子类；无表结构变更，无需 Alembic 迁移。
- 部署需在 `.env` / 环境变量配置白名单域、大小上限、超时；未配置时给出安全默认（仅 Polymarket 图片域）。
- 回滚：移除路由注册即可，无数据副作用。

## Open Questions

- Polymarket 图片域的确切域名清单（如 CDN 域）需技术方案阶段最终确认并写入 `.env` 默认白名单。
- 大小上限与超时的具体数值区间由技术方案确定（兼顾海报图片体积与滥用防护），本设计只约定其来自 `Settings`。
- 是否需要对解析 IP 做私网段拒绝（DNS rebinding 增强）留待技术方案评估，不改变 data-source §3 既有约束口径。
