from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_name: str = "Production AI Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    agent_api_key: str = "demo-key-change-in-production"
    allowed_origins: List[str] = ["*"]
    
    # Dependencies
    redis_url: str = "redis://localhost:6379/0"
    
    # LLM Settings
    openai_api_key: str = ""
    llm_model: str = "mock-agent-deployment"
    
    # Limits
    rate_limit_per_minute: int = 20
    daily_budget_usd: float = 10.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
