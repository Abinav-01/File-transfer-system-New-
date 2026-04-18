from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DropVault"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = "dropvault"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "dropvault"
    DATABASE_URL: str = "postgresql://dropvault:password@postgres:5432/dropvault"

    REDIS_URL: str = "redis://redis:6379/0"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password"
    MINIO_SECURE: bool = False

    MINIO_BUCKET_NAME: str = "dropvault"
    UPLOAD_RATE_LIMIT: int = 100
    UPLOAD_RATE_WINDOW_SECONDS: int = 3600
    DOWNLOAD_RATE_LIMIT: int = 120
    DOWNLOAD_RATE_WINDOW_SECONDS: int = 3600
    PASSWORD_FAILURE_LIMIT: int = 5
    PASSWORD_FAILURE_WINDOW_SECONDS: int = 900
    CLEANUP_INTERVAL_SECONDS: int = 300
    MAX_UPLOAD_SIZE_BYTES: int = 1073741824  # 1 GB default
    DEFAULT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    MAX_EXPIRATION_MINUTES: int = 10080  # 7 days

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
