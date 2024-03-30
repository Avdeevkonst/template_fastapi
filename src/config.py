from dotenv import load_dotenv
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


settings = Settings()  # pyright:ignore[reportCallIssue]
