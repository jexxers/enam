from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from types import TracebackType
from typing import Any, Iterable, Mapping


_CONFIGURED = False
_CONFIGURE_LOCK = threading.Lock()


_RESERVED_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


def _utc_isoformat(ts_seconds: float) -> str:
    # RFC3339-ish, UTC, with milliseconds: 2026-04-08T12:34:56.789Z
    dt = datetime.fromtimestamp(ts_seconds, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_json_default(value: Any) -> Any:
    # Best-effort serialization without extra dependencies.
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return repr(value)


def _tb_to_frames(tb: TracebackType | None) -> list[dict[str, Any]]:
    if tb is None:
        return []
    frames: list[dict[str, Any]] = []
    for frame_summary in traceback.extract_tb(tb):
        frames.append(
            {
                "source": frame_summary.filename,
                "line": frame_summary.lineno,
                "func": frame_summary.name,
                "code": frame_summary.line,
            }
        )
    return frames


@dataclass(frozen=True)
class JsonLoggingConfig:
    service_name: str | None = None
    service_version: str | None = None
    level: str = "INFO"
    redact_keys: tuple[str, ...] = (
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "authorization",
    )


class JsonFormatter(logging.Formatter):
    def __init__(self, cfg: JsonLoggingConfig):
        super().__init__()
        self._cfg = cfg
        self._redact_keys_lower = {k.lower() for k in cfg.redact_keys}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _utc_isoformat(record.created),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread": record.threadName,
        }

        if self._cfg.service_name or self._cfg.service_version:
            payload["service"] = {
                **({"name": self._cfg.service_name} if self._cfg.service_name else {}),
                **(
                    {"version": self._cfg.service_version}
                    if self._cfg.service_version
                    else {}
                ),
            }

        # Attach any user-provided structured fields via logger.extra
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in _RESERVED_ATTRS or key.startswith("_"):
                continue
            extras[key] = value

        if extras:
            payload.update(self._redact(extras))

        if record.exc_info:
            exc_type, exc, tb = record.exc_info
            payload["error"] = {
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": str(exc),
            }
            frames = _tb_to_frames(tb)
            if frames:
                payload["stack"] = frames
            # Keep a single log event; JSON escaping prevents multiline splitting.
            payload["stacktrace"] = "".join(
                traceback.format_exception(exc_type, exc, tb)
            )

        return json.dumps(
            payload,
            default=_safe_json_default,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def _redact(self, obj: Any) -> Any:
        if isinstance(obj, Mapping):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                if str(k).lower() in self._redact_keys_lower:
                    out[k] = "[REDACTED]"
                else:
                    out[k] = self._redact(v)
            return out
        if isinstance(obj, list):
            return [self._redact(v) for v in obj]
        return obj


def configure_logging(
    *,
    service_name: str | None = None,
    service_version: str | None = None,
    level: str | None = None,
    redact_keys: Iterable[str] = JsonLoggingConfig.redact_keys,
) -> None:
    """
    Configure process-wide JSON logging exactly once.

    - Emits newline-delimited JSON to stdout (1 event per line).
    - Idempotent: repeated calls are no-ops.
    - Supports structured fields via `extra={...}` on log calls.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    with _CONFIGURE_LOCK:
        if _CONFIGURED:
            return

        cfg = JsonLoggingConfig(
            service_name=service_name or os.getenv("SERVICE_NAME") or None,
            service_version=service_version or os.getenv("SERVICE_VERSION") or None,
            level=(level or os.getenv("LOG_LEVEL") or "INFO").upper(),
            redact_keys=tuple(redact_keys),
        )

        root = logging.getLogger()
        root.setLevel(cfg.level)

        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(cfg.level)
        handler.setFormatter(JsonFormatter(cfg))

        # Avoid duplicate handlers if something preconfigured logging.
        root.handlers.clear()
        root.addHandler(handler)

        # Common noisy loggers can be tuned via LOG_LEVEL; don't disable others.
        logging.captureWarnings(True)

        _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger (after calling `configure_logging()` once at startup).
    """
    return logging.getLogger(name)
