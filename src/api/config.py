"""配置中心 — 从 .env 读取配置，启动时验证必填项。"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 加载 .env（只在 config.py 中调用一次）
load_dotenv(BASE_DIR / "src" / "api" / ".env")


@dataclass
class Config:
    """全局配置。所有业务常量集中在此，代码中引用 Config.XXX。"""

    # ---- 应用 ----
    APP_NAME: str = os.getenv("APP_NAME", "AI Code Kit")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")

    # ---- 数据库 ----
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "app")
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "5"))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "20"))

    # ---- JWT ----
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # ---- AI ----
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "deepseek-v4-pro")
    AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "120"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "3"))

    # ---- 文件上传 ----
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(5 * 1024 * 1024)))  # 5MB
    ALLOWED_EXTENSIONS: list[str] = field(default_factory=lambda: os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt").split(","))

    # ---- 支付（按需） ----
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET: str = os.getenv("WECHAT_SECRET", "")
    WECHAT_MCHID: str = os.getenv("WECHAT_MCHID", "")
    WECHAT_API_KEY: str = os.getenv("WECHAT_API_KEY", "")

    # ---- Apify 1688 数据采集（按需） ----
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
    APIFY_ACTOR_ID: str = os.getenv("APIFY_ACTOR_ID", "zen-studio~1688-wholesale-scraper")
    APIFY_TIMEOUT: int = int(os.getenv("APIFY_TIMEOUT", "15"))
    APIFY_POLL_INTERVAL: int = int(os.getenv("APIFY_POLL_INTERVAL", "1"))
    APIFY_DAILY_FREE_LIMIT: int = int(os.getenv("APIFY_DAILY_FREE_LIMIT", "3"))

    @classmethod
    def validate(cls):
        """启动时校验必填配置。缺失报错，防止带病启动。"""
        required = [
            ("SECRET_KEY", cls.SECRET_KEY),
            ("JWT_SECRET_KEY", cls.JWT_SECRET_KEY),
            ("DB_HOST", cls.DB_HOST),
            ("DB_NAME", cls.DB_NAME),
        ]
        # AI 配置可选（如果项目不用AI可以跳过）
        missing = [name for name, val in required if not val or val == "change-me"]
        if missing:
            raise ValueError(f"❌ 必填配置缺失: {', '.join(missing)}。请检查 .env 文件。")
