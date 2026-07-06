## ADDED Requirements

### Requirement: 后端同源图片代理端点

系统 SHALL 提供一个后端图片代理端点，接收目标图片 URL 参数，转发 Polymarket 公开静态图片，并以**二进制图片流**（同源、非 `ApiResponse` 包裹）返回，供前端海报出图同源加载以规避 canvas 跨域污染。（PRD §1.4 / §4.5）

#### Scenario: 合法 Polymarket 图片成功代理

- **WHEN** 前端请求代理端点，目标 URL 为白名单内 Polymarket 图片域、`https`、响应为 `image/*` 且在大小上限内
- **THEN** 端点以同源方式返回该图片的二进制流，`Content-Type` 为原始图片类型，前端可将其绘入 canvas 而不触发跨域污染

#### Scenario: 缺少或空的目标 URL 参数

- **WHEN** 请求未携带目标图片 URL 参数或参数为空
- **THEN** 端点拒绝请求并返回业务异常（由全局 handler 转为统一错误响应），不发起任何出站请求

### Requirement: 图片域名白名单校验

系统 SHALL 仅允许目标 URL 的域名在**图片域名白名单**（仅 Polymarket 图片域）之内；白名单来自 `core/config.Settings`（`.env` / 环境变量），不得硬编码。非白名单域名一律拒绝。（data-source §3；PRD §1.4）

#### Scenario: 非白名单域名被拒绝

- **WHEN** 目标 URL 的域名不在配置的图片域名白名单内
- **THEN** 端点拒绝请求并返回业务异常，不发起任何出站请求

#### Scenario: 白名单域名放行

- **WHEN** 目标 URL 的域名在配置的图片域名白名单内且其余约束均满足
- **THEN** 端点放行并继续后续的协议与内容校验

### Requirement: 仅允许 https 协议

系统 SHALL 仅接受协议为 `https` 的目标 URL；`http` 及其它协议（如 `file`、`ftp`、`data`）一律拒绝。（data-source §3）

#### Scenario: 非 https 协议被拒绝

- **WHEN** 目标 URL 的协议不是 `https`
- **THEN** 端点拒绝请求并返回业务异常，不发起任何出站请求

### Requirement: 仅允许 image/* 内容类型

系统 SHALL 校验上游响应的 `Content-Type`，仅当其为 `image/*` 时才返回内容；非 `image/*`（如 `text/html`、`application/json`）一律拒绝。（data-source §3）

#### Scenario: 上游返回非图片内容类型被拒绝

- **WHEN** 上游响应的 `Content-Type` 不属于 `image/*`
- **THEN** 端点中止转发并返回业务异常，不把该响应体回传给前端

### Requirement: 响应大小上限

系统 SHALL 对上游响应体施加**大小上限**（来自 `core/config.Settings`）；无论上游是否声明 `Content-Length`，一旦累计读取字节数超过上限即中止拉取并拒绝。（data-source §3）

#### Scenario: 上游声明的大小超过上限

- **WHEN** 上游响应 `Content-Length` 超过配置的大小上限
- **THEN** 端点拒绝并返回业务异常，不完整下载该资源

#### Scenario: 流式读取累计超过上限

- **WHEN** 上游未声明 `Content-Length` 或声明值偏小，但流式读取过程中累计字节数超过配置上限
- **THEN** 端点中止读取并返回业务异常，不把超限内容回传给前端

### Requirement: 请求超时

系统 SHALL 对出站拉取上游图片的请求施加**超时**（来自 `core/config.Settings`）；超时后中止请求并返回业务异常。（data-source §3）

#### Scenario: 上游响应超时

- **WHEN** 出站拉取上游图片在配置的超时时间内未完成
- **THEN** 端点中止该出站请求并返回业务异常，不长时间挂起

### Requirement: 禁止跨域重定向

系统 SHALL 不自动跟随跨域重定向；当上游返回重定向时，重定向目标域名 MUST 仍在图片域名白名单内且协议为 `https`，否则拒绝。（data-source §3）

#### Scenario: 重定向到白名单外域名被拒绝

- **WHEN** 上游返回重定向，其目标域名不在图片域名白名单内（或协议非 `https`）
- **THEN** 端点拒绝并返回业务异常，不跟随该重定向

#### Scenario: 重定向仍在白名单内

- **WHEN** 上游返回重定向且目标仍为白名单内 `https` 图片域
- **THEN** 端点对重定向目标复用同一套白名单 / 协议 / 内容类型 / 大小 / 超时校验后再决定是否放行

### Requirement: 只读转发不改变数据口径

系统 SHALL 仅只读转发公开静态图片资源，不改写、不缓存业务数据、不改变任何数据口径；代理不承担 Polymarket 业务数据拉取职责。（data-source §3 / §5）

#### Scenario: 仅转发公开静态图片

- **WHEN** 端点代理一张合法 Polymarket 图片
- **THEN** 仅原样转发图片字节，不解析、不落库、不影响事件 / 选项 / 偏差等业务数据口径

### Requirement: 统一错误契约

系统 SHALL 在所有校验失败与上游异常路径上抛出 `core/exceptions.BusinessException` 及其子类，由全局异常 handler 统一转为错误响应；MUST NOT 裸抛 `HTTPException`、MUST NOT 返回错误字典。成功路径返回二进制图片流不包 `ApiResponse`。（PRD §1.4；后端 api-and-error-contract）

#### Scenario: 校验失败走统一错误响应

- **WHEN** 任一安全约束（白名单 / https / image-* / 大小 / 超时 / 重定向）校验失败
- **THEN** 端点抛出 `BusinessException` 子类，由全局 handler 转为统一错误响应结构，前端可据此展示明确失败态
