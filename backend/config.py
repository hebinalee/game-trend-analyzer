from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gametrend:changeme@db:5432/gametrend_db"
    anthropic_api_key: str = ""
    crawl_interval_hours: int = 6
    analyze_interval_hours: int = 24

    class Config:
        env_file = ".env"


settings = Settings()
