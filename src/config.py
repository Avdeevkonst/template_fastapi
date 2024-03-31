from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    APP_PORT: int

    SECRET_KEY: str
    ALGORITHMS: str

    PG_HOST: str
    PG_PORT: str
    PG_NAME: str
    PG_USER: str
    PG_PASS: str

    REDIS_HOST: str
    REDIS_PORT: str

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def db_url_postgresql(self) -> str:
        return (
            f"postgresql+asyncpg://{self.PG_USER}:{self.PG_PASS}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_NAME}"
        )

    @property
    def db_url_redis(self) -> str:
        return f"redis://@{self.REDIS_HOST}:{self.REDIS_PORT}/"

    @property
    def config_for_fastapi_mail(self) -> ConnectionConfig:  # pragma: no cover
        return ConnectionConfig(
            MAIL_USERNAME=self.MAIL_USERNAME,
            MAIL_PASSWORD=self.MAIL_PASSWORD,
            MAIL_FROM=self.MAIL_FROM,
            MAIL_PORT=self.MAIL_PORT,
            MAIL_SERVER=self.MAIL_SERVER,
            MAIL_FROM_NAME=self.MAIL_FROM_NAME,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
        )


settings = Settings()  # pyright:ignore[reportCallIssue]
