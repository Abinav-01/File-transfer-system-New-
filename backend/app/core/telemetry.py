"""Small Redis-backed counters shared by the API and Celery worker."""

import logging
from redis.exceptions import RedisError
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse

from app.core.redis import get_redis_client

KEY = "dropvault:metrics:v1"
COUNTERS = (
    "http_requests_total",
    "uploads_total",
    "downloads_success_total",
    "downloads_rejected_total",
    "files_expired_total",
    "files_deleted_total",
    "cleanup_failures_total",
    "rate_limit_rejected_total",
)
logger = logging.getLogger(__name__)


def increment(name: str) -> None:
    if name not in COUNTERS:
        raise ValueError("Unknown metric")
    try:
        get_redis_client().hincrby(KEY, name, 1)
    except RedisError:
        # Observability must not change a successful business operation.
        logger.warning("METRICS_UNAVAILABLE")


def observe_request(duration_seconds: float) -> None:
    try:
        client = get_redis_client()
        with client.pipeline(transaction=True) as pipe:
            pipe.hincrby(KEY, "http_requests_total", 1)
            pipe.hincrby(KEY, "http_request_duration_seconds_count", 1)
            pipe.hincrbyfloat(
                KEY, "http_request_duration_seconds_sum", duration_seconds
            )
            pipe.execute()
    except RedisError:
        logger.warning("METRICS_UNAVAILABLE")


def render_metrics() -> PlainTextResponse:
    try:
        values = get_redis_client().hgetall(KEY)
    except RedisError:
        raise HTTPException(503, detail="Metrics unavailable") from None
    lines = []
    for name in COUNTERS:
        lines.extend(
            (
                f"# TYPE dropvault_{name} counter",
                f"dropvault_{name} {int(values.get(name, 0))}",
            )
        )
    lines.extend(
        (
            "# TYPE dropvault_http_request_duration_seconds summary",
            f"dropvault_http_request_duration_seconds_count {int(values.get('http_request_duration_seconds_count', 0))}",
            f"dropvault_http_request_duration_seconds_sum {float(values.get('http_request_duration_seconds_sum', 0)):.6f}",
        )
    )
    return PlainTextResponse(
        "\n".join(lines) + "\n", media_type="text/plain; version=0.0.4"
    )
