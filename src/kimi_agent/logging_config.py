from __future__ import annotations

import logging
import sys
from typing import Optional


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(verbose: bool = False, logger_name: Optional[str] = None) -> logging.Logger:
    """
    Configure process-wide logging and return a scoped logger.

    The sprint skeleton favours standard library logging to keep dependencies light.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logger = logging.getLogger(logger_name or "kimi_agent")
    logger.debug("Logging configured with level %s", logging.getLevelName(level))
    return logger
