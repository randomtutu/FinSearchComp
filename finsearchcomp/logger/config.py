# src/logger/config.py
from __future__ import annotations
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DICT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # 不影响第三方库的 logger
    "formatters": {
        "standard": {
            # 文件名+行号+函数名
            "format": (
                "%(asctime)s %(levelname)-8s [%(name)s] "
                "%(filename)s:%(lineno)d %(funcName)s | %(message)s"
            )
        },
        "brief": {"format": "%(levelname)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": os.getenv("LOG_CONSOLE_LEVEL", "INFO"),
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": os.getenv("LOG_FILE_LEVEL", "DEBUG"),
            "formatter": "standard",
            "filename": str(LOG_DIR / "app.log"),
            "when": "midnight",      # 每天轮转
            "backupCount": 7,        # 保留 7 天
            "encoding": "utf-8",
        },
    },
    "loggers": {
        # 根 logger：项目里用 getLogger(__name__) 都会走到这
        "": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
        },
        # 示例：降低某些啰嗦库的日志级别
        "urllib3": {"level": "WARNING", "propagate": False},
    },
}

_configured = False

def setup_logging(level: str | None = None) -> None:
    """
    初始化 logging。可以传 level 覆盖默认级别。
    """
    global _configured
    if _configured:
        return
    cfg = DICT_CONFIG.copy()
    if level:
        cfg["loggers"][""]["level"] = level
    logging.config.dictConfig(cfg)
    _configured = True

def get_logger(name: str | None = None) -> logging.Logger:
    """
    取得一个带好配置的 logger。
    在第一次调用时自动初始化配置。
    """
    if not _configured and not logging.getLogger().handlers:
        setup_logging()
    return logging.getLogger(name)