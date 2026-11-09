from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从项目根目录 .env 读取。"""

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "校园食堂点评推荐"
    database_url: str = "sqlite+aiosqlite:///../data/canteen.db"
    secret_key: str = "dev-secret"
    access_token_minutes: int = 120
    refresh_token_days: int = 30
    allowed_email_domains: str = "edu.cn"
    # 开发模式：没有邮件服务，验证码直接在 send-code 响应里回传。生产必须关掉
    auth_echo_code: bool = True
    embedding_backend: str = "none"  # none | local | openai
    cors_origins: str = "http://localhost:5173"

    @property
    def allowed_email_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
