from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CrowdTest"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/crowdtest"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM
    anthropic_api_key: str = ""
    haiku_model: str = "claude-haiku-4-5-20251001"
    sonnet_model: str = "claude-sonnet-4-6"

    # Simulation defaults
    default_crowd_size: int = 50
    default_turns: int = 7
    batch_size: int = 8  # agents per batched LLM call
    engagement_threshold: float = 0.2  # ~20% of agents engage per turn

    model_config = {"env_file": ".env", "env_prefix": "CROWDTEST_"}


settings = Settings()
