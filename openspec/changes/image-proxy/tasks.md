## 后端

- [x] 1.1 首次编辑后端前先读 `docs/backend/standards/`（`implementation-workflow.md`、`file-organization.md`、`layer-definition.md`、`api-and-error-contract.md`、`infrastructure.md`）确认分层与响应/异常/配置约束。
- [x] 1.2 在 `app/core/config.py` 的 `Settings` 新增图片代理配置项：图片域名白名单（Polymarket 图片域，列表）、响应大小上限、请求超时、重定向跳转次数上限；给出安全默认值（仅 Polymarket 图片域），值可经 `.env` 覆盖，不硬编码（data-source §3）。
- [x] 1.3 在 `app/core/exceptions.py` 新增图片代理业务异常子类（如非法目标 `ImageProxyInvalidTargetException`、上游异常 `ImageProxyUpstreamException`），继承 `BusinessException`，分配 code 与 status_code。
- [x] 1.4 新增 `image-proxy` service（`app/services/`）：实现前置校验——目标 URL 非空、协议仅 `https`、host 命中白名单（精确/后缀域匹配，拒绝伪装域），任一不满足抛业务异常且不发出站请求（data-source §3）。
- [x] 1.5 在 service 中用 `httpx` 出站拉取上游图片：`follow_redirects=False`、显式 timeout 取自 `Settings`；校验响应 `Content-Type` 仅 `image/*`，否则中止抛异常（data-source §3）。
- [x] 1.6 在 service 中实现大小上限双重保护：`Content-Length` 超限直接拒绝；流式读取累加字节数超限即中止并抛异常（data-source §3）。
- [x] 1.7 在 service 中实现禁跨域重定向：遇 3xx 取 `Location`，对目标复检「仅 https + 白名单」，命中则受控再拉取（限跳转次数），否则抛异常（data-source §3）。
- [x] 1.8 新增图片代理路由（`app/api/v1/`，如 `image_proxy.py`）：接收目标图片 URL 查询参数，调用 service，成功返回二进制图片流（`StreamingResponse`，`media_type` 为上游校验通过的 `image/*`），不包 `ApiResponse`；并在应用路由注册处挂载该路由。
- [x] 1.9 确认校验失败与上游异常均抛 `BusinessException` 子类、经全局 handler 转统一错误响应，无裸抛 `HTTPException`、无返回错误字典（PRD §1.4 / api-and-error-contract）。
- [x] 1.10 补充 pytest 单测覆盖各安全约束验收场景：合法图片成功代理、空/缺 URL 拒绝、非白名单域拒绝、非 https 拒绝、非 image-* 内容类型拒绝、大小超限（声明与流式两种）拒绝、超时拒绝、跨域重定向拒绝、白名单内重定向复检放行（对应 specs 各 Scenario）。
- [x] 1.11 运行 `make lint`（ruff）+ `make test`（pytest）验证；无表结构变更，无需 Alembic 迁移。
