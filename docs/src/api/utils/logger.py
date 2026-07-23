"""日志工具 — 文件轮转 + 控制台双输出 + openid/token 脱敏。"""

import logging
import os
from logging.handlers import RotatingFileHandler
from config import Config

# 日志级别配置
LOG_LEVEL = Config.LOG_LEVEL

# 日志文件路径
LOG_DIR = Config.LOG_DIR
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志格式
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建日志处理器
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(LOG_LEVEL)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(LOG_LEVEL)

# 创建日志记录器
def get_logger(name: str) -> logging.Logger:
    """获取或创建指定名称的日志记录器，确保日志同时输出到文件和控制台。"""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # 避免重复添加处理器
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


def mask_openid(openid: str) -> str:
   
    if not openid or len(openid) <= 6:
        return "***"  # 过短的openid直接返回脱敏值
    return f"{openid[:6]}***"


def mask_token(token: str) -> str:
    
    if not token or len(token) <= 10:
        return "***"
    return f"{token[:10]}***"
