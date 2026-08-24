"""Class-aware logging configuration and debug tracing for VisualCPSA."""
from __future__ import annotations

import inspect
import logging
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar, cast

from visualcpsa.exceptions import ConfigurationError

LOG_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)s %(filename)s %(classname)s %(funcName)s:%(lineno)d %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
FunctionType = TypeVar("FunctionType", bound=Callable[..., Any])
_NO_OWNER = object()


class ClassNameFilter(logging.Filter):
    """Add a class name attribute to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Populate `classname` from explicit logging metadata or use a dash."""
        if not hasattr(record, "classname"):
            record.classname = "-"
        assert isinstance(record.classname, str), "logging classname must be text"
        return True


def normalize_log_level(level_name: str) -> str:
    """Validate and normalize a textual logging level."""
    if not isinstance(level_name, str) or not level_name.strip():
        raise ConfigurationError("Logging level must be a non-empty string.")
    normalized = level_name.strip().upper()
    if normalized not in VALID_LEVELS:
        raise ConfigurationError(f"Unsupported logging level {level_name!r}; expected one of {sorted(VALID_LEVELS)}.")
    assert normalized in VALID_LEVELS, "normalized logging level invariant failed"
    return normalized


def configure_logging(level_name: str, log_file: Path) -> Path:
    """Configure file logging, falling back to standard error if the file cannot be opened."""
    normalized = normalize_log_level(level_name)
    if not isinstance(log_file, Path):
        raise ConfigurationError("Log file must be represented by pathlib.Path.")
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, normalized))
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(log_file, encoding="utf-8")
        effective_path = log_file.resolve()
    except OSError as error:
        handler = logging.StreamHandler(sys.stderr)
        effective_path = Path.cwd() / "vcpsa.log"
        print(f"VisualCPSA could not open log file {log_file}: {error}. Logging to standard error.", file=sys.stderr)
    handler.setFormatter(formatter)
    handler.addFilter(ClassNameFilter())
    root_logger.addHandler(handler)
    logging.getLogger(__name__).info("Logging configured level=%s destination=%s", normalized, effective_path)
    assert root_logger.handlers, "logging must have at least one handler"
    return effective_path


def get_logger(owner: object = _NO_OWNER) -> logging.LoggerAdapter:
    """Return a logger adapter carrying a class name without requiring optional behavior at call sites."""
    if owner is _NO_OWNER:
        class_name = "-"
        module_name = __name__
    elif isinstance(owner, type):
        class_name = owner.__name__
        module_name = owner.__module__
    else:
        class_name = owner.__class__.__name__
        module_name = owner.__class__.__module__
    adapter = logging.LoggerAdapter(logging.getLogger(module_name), {"classname": class_name})
    assert isinstance(adapter, logging.LoggerAdapter), "logger adapter construction failed"
    return adapter


def _safe_value(value: Any) -> str:
    """Return a bounded representation suitable for debug logs."""
    rendered = repr(value)
    return rendered if len(rendered) <= 300 else rendered[:297] + "..."


def traced(function: FunctionType) -> FunctionType:
    """Log debug entry with arguments, exit with return value, and exceptions for a major function."""
    signature = inspect.signature(function)

    @wraps(function)
    def wrapper(*arguments: Any, **keyword_arguments: Any) -> Any:
        """Invoke the traced function while logging entry, exit, and exceptions."""
        bound = signature.bind_partial(*arguments, **keyword_arguments)
        owner = bound.arguments.get("self", None)
        logger = get_logger(owner)
        logged_arguments = {name: _safe_value(value) for name, value in bound.arguments.items() if name != "self"}
        logger.debug("ENTER %s arguments=%s", function.__qualname__, logged_arguments)
        try:
            result = function(*arguments, **keyword_arguments)
        except Exception:
            logger.exception("EXCEPTION %s %s %r %r", function.__qualname__, function.__name__, arguments, keyword_arguments)
            raise
        logger.debug("EXIT %s return=%s", function.__qualname__, _safe_value(result))
        return result

    return cast(FunctionType, wrapper)
