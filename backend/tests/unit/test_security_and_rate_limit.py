import uuid
from unittest.mock import Mock, patch
import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

from app.services.security_service import (
    generate_secure_token,
    get_password_hash,
    verify_password,
)
from app.core import rate_limit


def test_tokens_are_unique_and_url_safe():
    tokens = {generate_secure_token(16) for _ in range(100)}
    assert len(tokens) == 100
    assert all(
        token.isascii() and "/" not in token and "+" not in token for token in tokens
    )


def test_password_hashing_and_verification():
    hashed = get_password_hash("correct horse")
    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)
    assert not verify_password("incorrect", hashed)
    assert get_password_hash("correct horse") != hashed


def test_rate_limiter_atomic_count_and_rejection():
    fake = Mock()
    fake.eval.side_effect = [1, 2]
    identity = str(uuid.uuid4())
    with (
        patch.object(rate_limit, "get_redis_client", return_value=fake),
        patch.object(rate_limit, "increment"),
    ):
        rate_limit.check_limit("upload", identity, 1, 60)
        with pytest.raises(HTTPException) as error:
            rate_limit.check_limit("upload", identity, 1, 60)
    assert error.value.status_code == 429
    assert fake.eval.call_count == 2


def test_rate_limiter_fails_closed_when_redis_is_down():
    with patch.object(
        rate_limit, "get_redis_client", side_effect=RedisConnectionError()
    ):
        with pytest.raises(HTTPException) as error:
            rate_limit.check_limit("upload", "someone", 1, 60)
    assert error.value.status_code == 503
