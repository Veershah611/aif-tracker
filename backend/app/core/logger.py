"""
Structured logging configuration for the AIF Scrapper.
Provides file + console handlers with timestamped output.
"""

import logging
import sys
from pathlib import Path

from app.core.config import settings

# Ensure log directory exists
Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

# Format string
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configure root logger once
_configured = False


def _setup_logging():
    """Set up root logger with file and console handlers."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.
    Call this at the top of each module:
        logger = get_logger(__name__)
    """
    _setup_logging()
    return logging.getLogger(name)
