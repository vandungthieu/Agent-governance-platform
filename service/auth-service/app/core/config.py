from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "auth-service"
    API_V1_STR: str = "/api/v1"

    POSTGRES_HOST: str = Field(default="localhost", min_length=1)
    POSTGRES_PORT: int = 5433
    POSTGRES_DB: str = Field(default="agent_governance", min_length=1)
    POSTGRES_USER: str = Field(default="postgres", min_length=1)
    POSTGRES_PASSWORD: str = Field(default="change-me", min_length=1)
    DATABASE_ECHO: bool = False

    JWT_SECRET_KEY: str = Field(default="change-this-secret-in-production", min_length=16)
    JWT_ISSUER: str = "agent-governance-auth"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DEFAULT_USER_ROLE: str = "employee"
    DEFAULT_USER_SCOPES: str = "agent:run customer:read"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=("service/auth-service/.env", ".env"),
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
