from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="CEST Placas Backend", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    database_url: str = Field(
        default="mysql+pymysql://cest_user:cest_password@localhost:3306/cest_placas?charset=utf8mb4",
        alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")
    mysql_pool_pre_ping: bool = Field(default=True, alias="MYSQL_POOL_PRE_PING")
    mysql_pool_recycle: int = Field(default=3600, alias="MYSQL_POOL_RECYCLE")

    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="change_me", alias="ADMIN_PASSWORD")

    secret_key: str = Field(default="change_me_in_production", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip().lower() == "release":
            return False
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
