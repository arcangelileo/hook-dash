from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HookDash"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./hookdash.db"

    # Auth
    secret_key: str = "change-me-in-production-use-a-real-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Webhook limits
    max_body_size: int = 1_048_576  # 1MB

    # Plan limits
    free_max_endpoints: int = 2
    free_max_requests_per_day: int = 100
    free_retention_hours: int = 24

    pro_max_endpoints: int = 25
    pro_max_requests_per_day: int = 10_000
    pro_retention_days: int = 30

    team_max_endpoints: int = 999_999  # effectively unlimited
    team_max_requests_per_day: int = 100_000
    team_retention_days: int = 90

    model_config = {"env_prefix": "HOOKDASH_", "env_file": ".env"}


settings = Settings()
