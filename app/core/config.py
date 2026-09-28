from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "shekel-backend"
    app_env: str = "local"
    log_level: str = "INFO"

    kafka_enabled: bool = False
    kafka_brokers: str = "localhost:9092"
    kafka_client_id: str = "shekel-backend"
    kafka_group_id: str = "shekel-app"

    database_url: str = "postgresql+asyncpg://shekel:shekel@localhost:5432/shekel"
    outbox_poll_interval_seconds: float = 1.0

    redis_url: str = "redis://localhost:6379/0"

    session_secret: str = "change-me-local"
    session_cookie_name: str = "shekel_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7

    keycloak_issuer: str = "memory://"
    keycloak_audience: str = "shekel-api"
    keycloak_realm: str = "shekel"
    keycloak_test_secret: str = "change-me-oidc-test-at-least-32-bytes"
    keycloak_admin_url: str = "http://localhost:8080"
    keycloak_admin_client_id: str = "shekel-api"
    keycloak_admin_client_secret: str = ""

    elasticsearch_url: str = "memory://"

    http_timeout_seconds: float = 5.0
    http_max_retries: int = 3
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
