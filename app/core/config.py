from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Org Manager"
    env: str = "dev"
    database_url: str
    log_level: str = "INFO"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    fernet_keys: str = ""
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 60

    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"


settings = Settings()
