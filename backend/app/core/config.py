from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SecurePay Account API"
    environment: str = "development"
    database_url: str = "sqlite:///./securepay.db"
    session_secret: str = "local-only-change-this-secret-before-deployment"
    session_cookie_name: str = "securepay_session"
    session_ttl_hours: int = 168
    session_cookie_secure: bool = False
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    rate_limit_login_per_minute: int = Field(default=10, gt=0)
    rate_limit_register_per_minute: int = Field(default=5, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def validate_production(self) -> None:
        if self.environment.lower() == "production":
            if self.session_secret == "local-only-change-this-secret-before-deployment" or len(self.session_secret) < 32:
                raise RuntimeError("SESSION_SECRET must be a strong, unique production secret.")
            if not self.session_cookie_secure:
                raise RuntimeError("SESSION_COOKIE_SECURE must be enabled in production.")
            if not self.cors_origins or "*" in self.cors_origins:
                raise RuntimeError("Production CORS origins must be an explicit allowlist.")
            database_url = make_url(self.database_url)
            if database_url.get_backend_name() != "postgresql":
                raise RuntimeError("PostgreSQL is required in production.")
            if database_url.query.get("sslmode") != "verify-full":
                raise RuntimeError("Production DATABASE_URL must require PostgreSQL TLS with sslmode=verify-full.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
