from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from backend/.env (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/almanac.db"

    # Auth gate (Phase 5) — empty until the auth gate is built and deployed.
    admin_password: str = ""
    admin_session_secret: str = ""

    # Live Claude-assisted capture (Phase 7) — left empty on purpose until
    # explicitly approved, same pattern as Chegga's coaching feature.
    anthropic_api_key: str = ""


settings = Settings()
