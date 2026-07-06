## Why

分享海报由前端 DOM 出图，海报内需加载 Polymarket 的跨域图片；直接加载会污染 canvas 导致导出失败（PRD §1.4 / §4.5）。需要后端提供一个**同源图片代理**端点，让海报出图能以同源方式拉取这些公开静态图片。代理直接对外拉取任意 URL 会引入 SSRF / 开放代理风险，因此必须落地一组安全约束（data-source §3）。

## What Changes

- 新增后端图片代理端点：接收目标图片 URL，转发 Polymarket 公开静态图片，以**二进制流**（同源）返回给前端，供海报出图使用。
- 落地 SSRF 安全校验（data-source §3）：域名白名单（仅 Polymarket 图片域）、仅 `https`、仅 `image/*` 内容类型、响应大小上限、请求超时、禁止跟随跨域重定向。
- 白名单域、大小上限、超时等安全参数走 `core/config.Settings`（`.env` / 环境变量），不硬编码。
- 校验失败 / 上游异常统一抛 `BusinessException` 及子类，由全局 handler 转响应；成功路径为二进制图片流，不包 `ApiResponse`。
- 不改变任何数据口径，仅转发公开静态图片资源（data-source §3）。

## Capabilities

### New Capabilities
- `image-proxy`: 后端同源安全图片代理能力——为海报出图代理加载 Polymarket 图片，并施加防 SSRF / 开放代理的安全约束（白名单 / https / image-* / 大小 / 超时 / 禁跨域重定向）。

### Modified Capabilities
<!-- 无：本 change 不修改既有 capability 的 requirement。 -->

## Impact

- 后端：新增 `image-proxy` 资源域一条路由（api → services 校验/转发 → 出站 HTTP 客户端）；`core/config.Settings` 新增图片代理相关配置项；`core/exceptions` 复用/新增安全校验相关业务异常。
- 依赖：需要一个出站 HTTP 客户端（如 httpx）用于流式拉取上游图片并可控制重定向与超时。
- 前端：海报出图改为经该代理同源加载图片（属 share-poster change，不在本 change 范围）。
- 数据口径：无影响，仅转发公开静态图片。
