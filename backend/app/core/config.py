from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从项目根目录 .env 读取。"""

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "校园食堂点评推荐"
    database_url: str = "sqlite+aiosqlite:///../data/canteen.db"
    secret_key: str = "dev-secret"
    access_token_minutes: int = 120
    allowed_email_domains: str = "edu.cn"
    embedding_backend: str = "none"  # none | local | openai
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
