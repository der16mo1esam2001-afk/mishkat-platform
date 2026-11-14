from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MISHKAT API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    auth_mode: str = "development"  # development | supabase_jwks
    dev_auth_enabled: bool = True
    dev_auth_secret: str = "CHANGE-ME-BEFORE-ANY-SHARED-USE-32-CHARS-MINIMUM"
    supabase_jwks_url: str | None = None
    supabase_issuer: str | None = None
    jwt_audience: str = "authenticated"

    vitalis_db_url: str = "postgresql://mishkat_app:local-only-change-me@vitalis-db:5432/vitalis"
    aquanex_db_url: str = "postgresql://mishkat_app:local-only-change-me@aquanex-db:5432/aquanex"
    agronex_db_url: str = "postgresql://mishkat_app:local-only-change-me@agronex-db:5432/agronex"
    energis_db_url: str = "postgresql://mishkat_app:local-only-change-me@energis-db:5432/energis"
    nexora_db_url: str = "postgresql://mishkat_app:local-only-change-me@nexora-db:5432/nexora"

    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    request_timeout_seconds: float = 25.0

    @model_validator(mode="after")
    def enforce_production_guardrails(self):
        if self.environment.lower() == "production":
            if self.auth_mode != "supabase_jwks":
                raise ValueError("Production requires AUTH_MODE=supabase_jwks")
            if self.dev_auth_enabled:
                raise ValueError("DEV_AUTH_ENABLED must be false in production")
            if not self.supabase_jwks_url or not self.supabase_issuer:
                raise ValueError("Production requires SUPABASE_JWKS_URL and SUPABASE_ISSUER")
            if not self.supabase_jwks_url.startswith("https://") or not self.supabase_issuer.startswith("https://"):
                raise ValueError("Production identity URLs must use HTTPS")
            if "*" in self.allowed_origins or not self.allowed_origins:
                raise ValueError("Production CORS_ORIGINS must be explicit and must not contain '*'")
            if len(self.dev_auth_secret) < 32:
                raise ValueError("DEV_AUTH_SECRET must remain at least 32 characters even when development auth is disabled")
            unsafe_fragments = ("CHANGE-ME", "replace-with", "local-please-change", "YOUR_PROJECT_REF")
            if any(fragment.lower() in value.lower() for value in [self.dev_auth_secret, *self.database_urls.values()] for fragment in unsafe_fragments):
                raise ValueError("Production configuration contains a known placeholder secret or database URL")
        if not (1 <= self.request_timeout_seconds <= 120):
            raise ValueError("REQUEST_TIMEOUT_SECONDS must be between 1 and 120")
        return self

    @property
    def database_urls(self) -> dict[str, str]:
        return {
            "vitalis": self.vitalis_db_url,
            "aquanex": self.aquanex_db_url,
            "agronex": self.agronex_db_url,
            "energis": self.energis_db_url,
            "nexora": self.nexora_db_url,
        }

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
