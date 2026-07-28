from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Governance Proxy"
    API_V1_STR: str = "/api/v1"
    
    # OpenAI Upstream API
    OPENAI_API_KEY: str = "your-openai-key-here"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    class Config:
        env_file = ".env"

settings = Settings()