from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gametrend:changeme@db:5432/gametrend_db"
    anthropic_api_key: str = ""
    crawl_interval_hours: int = 6
    analyze_interval_hours: int = 24
    slack_webhook_url: str = ""          # 미설정 시 알림 비활성화
    dashboard_url: str = "http://localhost:3000"
    # Reddit OAuth2 (https://www.reddit.com/prefs/apps 에서 "script" 앱 등록)
    # 미설정 시 Reddit 크롤링 비활성화
    reddit_client_id: str = ""
    reddit_client_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
