"""Small, atomic fixed-window Redis limiter. Redis outages fail closed (503)."""

import hashlib
import logging

from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import get_redis_client
from app.core.logging import domain_event
from app.core.telemetry import increment

logger = logging.getLogger(__name__)

# INCR and first-key expiry must be one atomic operation.
_INCREMENT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""


def _key(kind: str, identity: str) -> str:
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return f"dropvault:rate:{kind}:{digest}"


def client_identity(request: Request) -> str:
    # Never trust a caller-supplied forwarding header without a trusted proxy setup.
    return request.client.host if request.client else "unknown"


def _redis_call(operation):
    try:
        return operation(get_redis_client())
    except RedisError:
        logger.warning("Rate-limit Redis unavailable")
        raise HTTPException(503, detail="Rate limiting unavailable") from None


def check_limit(kind: str, identity: str, limit: int, window_seconds: int) -> None:
    count = _redis_call(
        lambda client: client.eval(_INCREMENT, 1, _key(kind, identity), window_seconds)
    )
    if count > limit:
        increment("rate_limit_rejected_total")
        domain_event("RATE_LIMIT_REJECTED", reason=kind)
        raise HTTPException(
            429,
            detail="Rate limit reached",
            headers={"Retry-After": str(window_seconds)},
        )


def check_password_lock(identity: str) -> None:
    count = _redis_call(lambda client: int(client.get(_key("password", identity)) or 0))
    if count >= settings.PASSWORD_FAILURE_LIMIT:
        increment("rate_limit_rejected_total")
        domain_event("RATE_LIMIT_REJECTED", reason="password")
        raise HTTPException(
            429,
            detail="Too many incorrect passwords",
            headers={"Retry-After": str(settings.PASSWORD_FAILURE_WINDOW_SECONDS)},
        )


def record_password_failure(identity: str) -> None:
    _redis_call(
        lambda client: client.eval(
            _INCREMENT,
            1,
            _key("password", identity),
            settings.PASSWORD_FAILURE_WINDOW_SECONDS,
        )
    )


def clear_password_failures(identity: str) -> None:
    _redis_call(lambda client: client.delete(_key("password", identity)))
