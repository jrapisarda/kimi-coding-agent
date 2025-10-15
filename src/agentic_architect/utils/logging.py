"""Logging utilities with Rich integration."""

from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def configure_logging(level: int = logging.INFO) -> None:
    """Configure standard logging with Rich handler."""

    console = Console()
    handler = RichHandler(console=console, show_time=True, show_path=False)
    logging.basicConfig(level=level, handlers=[handler], format="%(message)s")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a configured logger."""

    return logging.getLogger(name or __name__)


__all__ = ["configure_logging", "get_logger"]
