# app/core/exceptions.py


class BusinessException(Exception):
    """业务异常基类。"""

    def __init__(
        self,
        code: int,
        message: str,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UsernameAlreadyExistsException(BusinessException):
    """用户名已存在。"""

    def __init__(self):
        super().__init__(
            code=40001,
            message="Username already exists",
            status_code=400,
        )


class LoginFailedException(BusinessException):
    """登录失败（用户名或密码错误）。"""

    def __init__(self):
        super().__init__(
            code=40101,
            message="Invalid username or password",
            status_code=401,
        )


class LoginLockedException(BusinessException):
    """登录失败次数过多，账号暂时锁定。"""

    def __init__(self):
        super().__init__(
            code=42901,
            message="Too many login failures, please try again later",
            status_code=429,
        )


class TokenRevokedException(BusinessException):
    """Token 已失效（已退出登录）。"""

    def __init__(self):
        super().__init__(
            code=40102,
            message="Token has been revoked",
            status_code=401,
        )


class ImageProxyInvalidTargetException(BusinessException):
    """图片代理目标非法（缺失 / 空 / 非 https / 非白名单域）。"""

    def __init__(self, message: str = "Invalid image proxy target"):
        super().__init__(
            code=40002,
            message=message,
            status_code=400,
        )


class ImageProxyUpstreamException(BusinessException):
    """图片代理上游异常（超时 / 连接失败 / 非图片类型 / 超出大小上限）。"""

    def __init__(self, message: str = "Image proxy upstream error"):
        super().__init__(
            code=50201,
            message=message,
            status_code=502,
        )


class ImageUploadInvalidException(BusinessException):
    """图片上传参数非法（空文件 / 非图片类型 / 超过大小上限）。"""

    def __init__(self, message: str = "Invalid image upload"):
        super().__init__(
            code=40003,
            message=message,
            status_code=400,
        )


class UpstreamUnavailableException(BusinessException):
    """上游（Polymarket）拉取失败且无缓存快照可回退，返回明确错误态。"""

    def __init__(
        self,
        message: str = "Upstream market data is temporarily unavailable",
    ):
        super().__init__(
            code=50301,
            message=message,
            status_code=503,
        )


class EventNotFoundException(BusinessException):
    """事件输入无法解析到有效 Polymarket 事件（明确「未找到」空态，不静默失败）。"""

    def __init__(self, message: str = "Event not found"):
        super().__init__(
            code=40401,
            message=message,
            status_code=404,
        )


class RateLimitExceededException(BusinessException):
    """实时路径请求超过服务端限流阈值（按 IP / 会话），返回 429。"""

    def __init__(
        self,
        message: str = "Too many requests, please try again later",
    ):
        super().__init__(
            code=42902,
            message=message,
            status_code=429,
        )
