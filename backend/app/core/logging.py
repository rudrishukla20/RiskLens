import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from app.core.config import settings

# Thread-safe request logging context
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
method_ctx: ContextVar[str] = ContextVar("method", default="")
path_ctx: ContextVar[str] = ContextVar("path", default="")
status_code_ctx: ContextVar[Optional[int]] = ContextVar("status_code", default=None)
duration_ms_ctx: ContextVar[Optional[float]] = ContextVar("duration_ms", default=None)
ip_address_ctx: ContextVar[str] = ContextVar("ip_address", default="")


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as structured JSON including thread context values."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger_name": record.name,
            "request_id": request_id_ctx.get(),
            "user_id": user_id_ctx.get(),
            "method": method_ctx.get(),
            "path": path_ctx.get(),
            "status_code": status_code_ctx.get(),
            "duration_ms": duration_ms_ctx.get(),
            "ip_address": ip_address_ctx.get(),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def custom_rotation_namer(default_name: str) -> str:
    """
    Overrides default TimedRotatingFileHandler backup naming structure.
    Generates dd:mm:yyyy_hh:mm:ss.log on Linux, and dd-mm-yyyy_hh-mm-ss.log elsewhere.
    """
    now = time.localtime()
    is_linux = sys.platform.startswith("linux")
    if is_linux:
        time_str = time.strftime("%d:%m:%Y_%H:%M:%S", now)
    else:
        time_str = time.strftime("%d-%m-%Y_%H-%M-%S", now)

    log_dir = os.path.dirname(default_name)
    return os.path.join(log_dir, f"{time_str}.log")


def setup_app_logging() -> logging.Logger:
    """Configures centralized logging system."""
    logger = logging.getLogger("risklens")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Avoid adding duplicate handlers
    if not logger.handlers:
        os.makedirs(settings.LOG_DIR, exist_ok=True)

        # 1. Console Handler (for Docker logs aggregation)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredJSONFormatter())
        logger.addHandler(console_handler)

        # 2. File Handler (Hourly Rotating)
        log_filepath = os.path.join(settings.LOG_DIR, "risklens.log")
        file_handler = TimedRotatingFileHandler(
            filename=log_filepath,
            when=settings.LOG_ROTATE_WHEN,
            interval=settings.LOG_ROTATE_INTERVAL,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(StructuredJSONFormatter())
        file_handler.namer = custom_rotation_namer
        logger.addHandler(file_handler)

        logger.propagate = False

    return logger


# Initialize logger on module load
logger = setup_app_logging()
