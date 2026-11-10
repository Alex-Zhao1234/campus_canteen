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
    # 是否需要验证码。false = 邮件服务关闭，输入校园邮箱直接登录（内测/演示用，身份未验证）
    auth_code_required: bool = True
    # 开发模式：没有邮件服务，验证码直接在 send-code 响应里回传。生产必须关掉
    auth_echo_code: bool = True
    embedding_backend: str = "none"  # none | local | openai
    cors_origins: str = "http://localhost:5173"
    # 定时任务：榜单重算间隔；测试/脚本环境可关掉调度器
    scheduler_enabled: bool = True
    # 演示环境：评价表为空时启动写入一批演示评价（Render 免费实例休眠后数据清空）
    seed_demo_reviews: bool = False
    # 单容器部署：前端构建产物目录，非空则由 FastAPI 托管并做 SPA 回退
    static_dir: str | None = None
    ranking_interval_minutes: int = 10
    # 座位模拟器：没有真实传感器时扮演网关，按餐段曲线生成座位进出（演示用）
    seat_simulator_enabled: bool = False
    seat_sim_interval_seconds: int = 5

    @property
    def allowed_email_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
