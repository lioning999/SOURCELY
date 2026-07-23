# -*- coding: utf-8 -*-
# OfferCopilot 配置 — 所有业务常量从 .env 读取，代码不写死

import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)


class Config:
    # ── 数据库 ──────────────────────────────
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "3306"))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")

    # ── JWT ─────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # ── 微信登录 ─────────────────────────────
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "")
    WECHAT_SECRET: str = os.getenv("WECHAT_SECRET", "")
    WECHAT_LOGIN_URL: str = os.getenv("WECHAT_LOGIN_URL", "https://api.weixin.qq.com/sns/oauth2/access_token")
    DOMAIN: str = os.getenv("DOMAIN", "")

    # ── 微信支付 ─────────────────────────────
    WECHAT_PAY_APPID: str = os.getenv("WECHAT_PAY_APPID", "")
    WECHAT_PAY_MCH_ID: str = os.getenv("WECHAT_PAY_MCH_ID", "")
    WXPAY_APIV3_KEY: str = os.getenv("WXPAY_APIV3_KEY", "")
    WXPAY_CERT_SERIAL_NO: str = os.getenv("WXPAY_CERT_SERIAL_NO", "")
    WXPAY_PRIVATE_KEY_PATH: str = os.getenv("WXPAY_PRIVATE_KEY_PATH", "")
    WXPAY_PUBLIC_KEY_ID: str = os.getenv("WXPAY_PUBLIC_KEY_ID", "")
    WXPAY_PUBLIC_KEY_PATH: str = os.getenv("WXPAY_PUBLIC_KEY_PATH", "")
    WECHAT_PAY_NOTIFY_URL: str = os.getenv("WECHAT_PAY_NOTIFY_URL", "")

    # ── AI ──────────────────────────────────
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    AI_MODEL_NAME: str = os.getenv("AI_MODEL_NAME", "deepseek-v4-pro")
    AI_REQUEST_TIMEOUT: float = float(os.getenv("AI_REQUEST_TIMEOUT", "60"))
    AI_DIAGNOSE_TIMEOUT: float = float(os.getenv("AI_DIAGNOSE_TIMEOUT", "120"))
    AI_OPTIMIZE_TIMEOUT: float = float(os.getenv("AI_OPTIMIZE_TIMEOUT", "180"))
    AI_CONNECT_TIMEOUT: float = float(os.getenv("AI_CONNECT_TIMEOUT", "10"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "3"))
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "4096"))

    # ── 业务常量 ─────────────────────────────
    # ── 支付套餐 ───────────────────────────
    PLAN_1_PRICE: int = int(os.getenv("PLAN_1_PRICE", "100"))   # ¥1，1 次优化
    PLAN_1_TIMES: int = int(os.getenv("PLAN_1_TIMES", "1"))
    RESUME_TEXT_MAX_LENGTH: int = int(os.getenv("RESUME_TEXT_MAX_LENGTH", "10000"))
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt").split(",")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "5242880"))  # 5MB

    # ── 服务器 ──────────────────────────────
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"

    # ── 日志 ─────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")

    # ── 启动校验 ─────────────────────────────
    @classmethod
    def validate(cls):
        required = [
            "DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD",
            "JWT_SECRET_KEY",
            "WECHAT_APPID", "WECHAT_SECRET", "DOMAIN",
            "DASHSCOPE_API_KEY",
        ]
        missing = [k for k in required if not getattr(cls, k, None)]
        if missing:
            raise ValueError(f"缺少必要环境变量: {', '.join(missing)}")
        # 支付配置仅在生产环境校验
        if not cls.TEST_MODE:
            pay_required = [
                "WECHAT_PAY_APPID", "WECHAT_PAY_MCH_ID", "WXPAY_APIV3_KEY",
                "WXPAY_CERT_SERIAL_NO", "WECHAT_PAY_NOTIFY_URL",
            ]
            pay_missing = [k for k in pay_required if not getattr(cls, k, None)]
            if pay_missing:
                raise ValueError(f"缺少支付环境变量: {', '.join(pay_missing)}")
