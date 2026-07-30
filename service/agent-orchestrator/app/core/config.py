from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "agent-orchestrator"
    API_V1_STR: str = "/api/v1"

    LLM_PROVIDER: str = Field(min_length=1)
    OLLAMA_BASE_URL: str = Field(min_length=1)
    OLLAMA_MODEL: str = Field(min_length=1)
    LLM_TIMEOUT_SECONDS: float

    EMBEDDING_PROVIDER: str = "ollama"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 768
    EMBEDDING_TIMEOUT_SECONDS: float = 60

    POSTGRES_HOST: str = Field(min_length=1)
    POSTGRES_PORT: int
    POSTGRES_DB: str = Field(min_length=1)
    POSTGRES_USER: str = Field(min_length=1)
    POSTGRES_PASSWORD: str = Field(min_length=1)
    DATABASE_ECHO: bool

    WEB_SEARCH_ENABLED: bool
    WEB_SEARCH_TIMEOUT_SECONDS: float
    WEB_SEARCH_MAX_RESULTS: int

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=("service/agent-orchestrator/.env", ".env"),
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
