"""Logging configuration utilities."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string for log messages

    Returns:
        Configured root logger
    """
    if format_string is None:
        format_string = "%(asctime)s %(levelname)s %(name)s: %(message)s"

    logging.basicConfig(
        level=level,
        format=format_string,
        stream=sys.stdout,
    )

    return logging.getLogger("pocket_studio")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"pocket_studio.{name}")