from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    redis_url: str = "redis://localhost:6379/0"

    # 图片代理（image-proxy）安全参数：默认仅覆盖 Polymarket 图片域，
    # 可经 .env / 环境变量覆盖（列表支持逗号分隔字符串或 JSON 数组）。
    image_proxy_allowed_hosts: list[str] = [
        "polymarket.com",
        "polymarket-upload.s3.us-east-2.amazonaws.com",
    ]
    image_proxy_max_bytes: int = 5 * 1024 * 1024
    image_proxy_timeout_seconds: float = 10.0
    image_proxy_max_redirects: int = 3

    # ---------------- Polymarket 数据接入（poly-data-integration） ----------------
    # Gamma / CLOB 双 API base URL（只读拉取元数据 / 价格）。
    polymarket_gamma_base_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_base_url: str = "https://clob.polymarket.com"
    polymarket_request_timeout_seconds: float = 10.0

    # 分层 TTL（秒）：元数据/列表分钟级、价格/赔率秒~十秒级；
    # fallback_ttl 为降级快照保留时长（供上游失败时回退，即使已过期）。
    market_metadata_ttl: int = 300
    market_price_ttl: int = 10
    market_fallback_ttl: int = 86400

    # 定时预取：开关、频率与单次批量上限（受上游限流约束）。
    market_prefetch_enabled: bool = False
    market_prefetch_interval_seconds: int = 60
    market_prefetch_batch_limit: int = 20

    # 上游指数退避重试参数（基础间隔 / 最大重试次数 / 单次退避上限）。
    market_retry_base_delay_seconds: float = 0.5
    market_retry_max_attempts: int = 4
    market_retry_max_delay_seconds: float = 8.0

    # 世界杯筛选：标签与关键词（逗号分隔，同一数据源仅筛选）。
    world_cup_tags: str = "world-cup,soccer,football"
    world_cup_keywords: str = "world cup,worldcup"

    # 可测性：Mock/故障注入开关（非生产）。fault_mode 取值见 PolymarketClient。
    polymarket_mock_enabled: bool = False
    polymarket_fault_mode: str = ""

    # ---------------- 分析对外 API（analysis-api） ----------------
    # 默认事件列表每页返回上限（首屏不无限堆叠，PRD §4.1）。
    event_list_page_size: int = 20
    # 多事件排行每榜默认 TopN 截取（PRD §4.4、bias-algorithm §5）。
    ranking_top_n: int = 10
    # 名称搜索默认返回候选上限。
    event_search_limit: int = 10
    # 实时路径（搜索 / slug 解析拉取 / 明细刷新）按 IP·会话限流窗口（秒）与窗口内阈值。
    realtime_rate_limit_window: int = 60
    realtime_rate_limit_max: int = 30

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def world_cup_tag_list(self) -> list[str]:
        """世界杯筛选标签列表（去空、小写归一）。"""
        return [t.strip().lower() for t in self.world_cup_tags.split(",") if t.strip()]

    @property
    def world_cup_keyword_list(self) -> list[str]:
        """世界杯筛选关键词列表（去空、小写归一）。"""
        return [
            k.strip().lower() for k in self.world_cup_keywords.split(",") if k.strip()
        ]

    @field_validator("image_proxy_allowed_hosts", mode="before")
    @classmethod
    def _split_allowed_hosts(cls, value: object) -> object:
        # 允许在 .env 里用逗号分隔字符串配置白名单（非 JSON 数组），
        # 便于运维；同时保留原始 list / JSON 解析行为。
        if isinstance(value, str) and not value.strip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()
