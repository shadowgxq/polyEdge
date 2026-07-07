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

    # 图片上传：用于分享海报先上传后分发 URL。默认保存到 backend/uploads/images，
    # 经 /uploads 静态路径对外提供访问。
    upload_storage_dir: str = "uploads"
    image_upload_max_bytes: int = 5 * 1024 * 1024
    image_upload_allowed_types: list[str] = ["image/png", "image/jpeg", "image/webp"]

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
    # 默认开启：启动即预热默认列表入缓存，避免首个请求冷启动同步回源阻塞首屏。
    market_prefetch_enabled: bool = True
    market_prefetch_interval_seconds: int = 30
    market_prefetch_batch_limit: int = 100
    # 请求触发刷新意图的限频窗口：同一列表 / 单事件在窗口内只允许一个后台刷新任务。
    market_refresh_throttle_seconds: int = 30

    # 上游指数退避重试参数（基础间隔 / 最大重试次数 / 单次退避上限）。
    market_retry_base_delay_seconds: float = 0.5
    market_retry_max_attempts: int = 4
    market_retry_max_delay_seconds: float = 8.0

    # 详情请求路径是否逐 outcome 取 CLOB midpoint。默认关闭：请求线程只做 1 次 Gamma
    # 拉取（用内联 outcomePrices），避免多市场事件的 midpoint 扇出把请求拖到超时；
    # 更新鲜的 midpoint 交由后台摄取任务离线补齐（serving 永不被上游拖慢）。
    market_detail_use_midpoint: bool = False

    # 世界杯筛选：默认列表按 FIFA 世界杯 tag 服务端拉取（等价 /sports/world-cup 页面口径），
    # tags/keywords 作服务端结果的防御性二次收敛（同一数据源，仅筛选）。
    world_cup_tag_slug: str = "2026-fifa-world-cup"
    world_cup_tags: str = "world-cup,soccer,football,fifa-world-cup,2026-fifa-world-cup"
    world_cup_keywords: str = "world cup,worldcup"

    # 可测性：Mock/故障注入开关（非生产）。fault_mode 取值见 PolymarketClient。
    polymarket_mock_enabled: bool = False
    polymarket_fault_mode: str = ""

    # ---------------- 分析对外 API（analysis-api） ----------------
    # 默认事件列表每页返回上限（首屏不无限堆叠，PRD §4.1）。
    event_list_page_size: int = 20
    # 列表卡片每个事件的选项预览上限（按概率降序取 TopN，其余进详情页）。
    event_card_option_preview: int = 5
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

    @field_validator("image_upload_allowed_types", mode="before")
    @classmethod
    def _split_upload_allowed_types(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()
