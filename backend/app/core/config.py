from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./oist_erp.db"
    jwt_secret_key: str = "development-only-secret-change-before-use-32chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60
    seed_default_password: str = ""
    upload_dir: str = "uploads"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
