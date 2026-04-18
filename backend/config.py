from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gametrend:changeme@db:5432/gametrend_db"
    anthropic_api_key: str = ""
    crawl_interval_hours: int = 6
    analyze_interval_hours: int = 24
    slack_webhook_url: str = ""          # 미설정 시 알림 비활성화
    dashboard_url: str = "http://localhost:3000"
    data_dir: str = "./data"             # 로컬 파일 저장 루트 디렉터리

    class Config:
        env_file = ".env"


settings = Settings()
