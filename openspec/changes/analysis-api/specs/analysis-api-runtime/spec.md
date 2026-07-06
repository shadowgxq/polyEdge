## ADDED Requirements

### Requirement: 统一 ApiResponse 响应封装

系统 SHALL 使所有对外分析接口返回统一 `ApiResponse[T]` 信封（`code=0` 表成功，经 `success_response(data=...)` 返回），出参为 Pydantic 出参模型（snake_case），MUST NOT 手拼字典或返回裸数据模型。来源：PRD §1.4、api-and-error-contract.md。

#### Scenario: 成功响应统一信封

- **WHEN** 任一分析接口成功返回数据
- **THEN** 响应为 `{ code: 0, message, data }` 信封，`data` 为对应 Pydantic 出参模型

#### Scenario: 出参为定义好的响应模型

- **WHEN** 装配接口返回数据
- **THEN** 返回值经声明的 `response_model=ApiResponse[T]` 校验，不返回裸 ORM/领域对象或手拼 dict

### Requirement: 上游不可用转业务错误态

系统 SHALL 在组合层遇到上游不可用（`poly-data-integration` 拉取失败且无缓存快照抛出的 `UpstreamUnavailableException`）时不吞异常，交由全局异常 handler 转成 `ApiResponse` 错误态（非 `code=0`）供前端重试，MUST NOT 返回空的成功结果或静默失败。来源：PRD §5.2/§5.3、data-source §4/§5。

#### Scenario: 上游不可用且无缓存

- **WHEN** 组合层调用数据读取遇到 `UpstreamUnavailableException`
- **THEN** 该异常上抛由全局 handler 转为 `ApiResponse` 错误态，携带用户可读 message 供前端重试

#### Scenario: 回退缓存快照带快照时间

- **WHEN** 上游拉取失败但存在（含过期）缓存快照，数据层回退该快照
- **THEN** 接口正常返回该快照结果并透传其 `data_snapshot_at`，不谎称为最新数据

### Requirement: 数据边界作为成功响应内标注

系统 SHALL 将数据边界（事件「不适用偏差分析」、选项被排除、全事件退化为纯交易热度）作为**成功响应内的标注字段**返回，而非错误态；这些标注供前端展示降级/边界提示。来源：PRD §5.2、bias-algorithm §3.5/§6。

#### Scenario: 退化与边界随成功响应返回

- **WHEN** 事件触发纯交易热度退化、或含被排除选项、或整体不适用偏差分析
- **THEN** 接口以成功响应返回结果并在对应字段标注该边界状态，不转为错误态

### Requirement: 实时路径服务端限流

系统 SHALL 对绕过预取缓存的实时请求（事件名称搜索、slug 解析拉取、单事件明细刷新）按 IP / 会话施加服务端限流（经 Redis 计数，窗口与阈值经配置读取）；超过阈值 MUST 抛业务异常（HTTP 429）由全局 handler 转 `ApiResponse` 错误态。限流计数因 Redis 故障不可用时按 fail-open 处理（本次不拦截），不阻断主流程。来源：data-source §5、infrastructure.md。

#### Scenario: 实时请求超阈值被限流

- **WHEN** 同一 IP / 会话在配置窗口内对实时路径的请求数超过阈值
- **THEN** 系统抛业务限流异常（HTTP 429），由全局 handler 转 `ApiResponse` 错误态

#### Scenario: 未超阈值正常放行

- **WHEN** 同一 IP / 会话在窗口内请求数未超阈值
- **THEN** 请求正常处理并返回结果

#### Scenario: 限流计数故障 fail-open

- **WHEN** Redis 计数操作因故障不可用
- **THEN** 本次请求不被限流拦截（fail-open），主流程不中断
