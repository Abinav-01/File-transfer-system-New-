import secrets
import bcrypt


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random url-safe token."""
    return secrets.token_urlsafe(length)


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
