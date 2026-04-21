import logging

# Define a custom TRACE level (lower than DEBUG) for ultra‑fine‑grained logs
TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


def _trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws)


logging.Logger.trace = _trace
import sys
from typing import Any

import structlog

# Basic structlog configuration – JSON output to stdout
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Return a structlog-bound logger with level set from settings.

    The logger is configured to output JSON lines. The underlying ``logging``
    logger level is also synchronized with the ``LOG_LEVEL`` setting so that
    any third‑party libraries that use the standard ``logging`` module respect
    the same verbosity.
    """
    # Ensure the standard logging logger exists for compatibility
    std_logger = logging.getLogger(name)
    if not std_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        std_logger.addHandler(handler)

    # Pull level from configuration
    from .config import get_settings

    level_name = get_settings().LOG_LEVEL
    level = getattr(logging, level_name, logging.INFO)
    std_logger.setLevel(level)

    # Return a structlog logger bound to the same name
    return structlog.get_logger(name)
