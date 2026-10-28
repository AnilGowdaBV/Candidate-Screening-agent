"""Structured, sanitized logging for Candidate Screening Agent."""

import logging
import re
import sys
from typing import Optional

# Patterns to scrub from any log message
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|token|secret|authorization|api[-_]?key)[=:\s\"']+(\S+)", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9_]{36,}", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]{60,}", re.IGNORECASE),
]


class SanitizedFormatter(logging.Formatter):
    """Log formatter that automatically masks passwords and tokens."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SENSITIVE_PATTERNS:
            if pattern.groups >= 1:
                sanitized = pattern.sub(r"\1=***REDACTED***", sanitized)
            else:
                sanitized = pattern.sub(r"***REDACTED***", sanitized)
        return sanitized


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure application-wide logger."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Root application logger
    logger = logging.getLogger("screening_agent")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers on reload
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = SanitizedFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a child logger under the screening_agent namespace."""
    base = logging.getLogger("screening_agent")
    if name:
        return base.getChild(name)
    return base
