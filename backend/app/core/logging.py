"""JSON logs with a request-scoped correlation ID and a safe field allowlist."""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
        }
        # Do not serialize arbitrary extra fields, exception arguments, or stack traces.
        for name in (
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "upload_id",
            "reason",
            "error_type",
        ):
            value = getattr(record, name, None)
            if value is not None:
                data[name] = value
        return json.dumps(data, separators=(",", ":"), default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True


def domain_event(event: str, **fields) -> None:
    allowed = {
        name: value
        for name, value in fields.items()
        if name in ("upload_id", "reason", "error_type")
    }
    level = (
        logging.ERROR
        if event.endswith("FAILURE")
        else logging.WARNING
        if event.endswith("REJECTED")
        else logging.INFO
    )
    logging.getLogger("dropvault.domain").log(
        level, event, extra={"event": event, **allowed}
    )
