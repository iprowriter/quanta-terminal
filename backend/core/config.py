from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).parents[1] / ".env"
load_dotenv(_ROOT_ENV)


class Settings(BaseSettings):
    # App
    app_name: str = "Quanta Terminal"
    environment: str = "development"
    # LLM
    google_api_key: str = Field(default="")

    # LangSmith
    langchain_api_key: str = Field(default="")
    langchain_tracing_v2: str = Field(default="true")
    langchain_project: str = Field(default="quanta-terminal")

    # provider info
    gemini_model: str = "gemini-2.5-flash-lite"
    ollama_model: str = "llama3.2:latest"
    model_provider: str = "google_genai"
    llm_provider: str  = "gemini"       # agents: 'gemini' | 'ollama'
    memo_writer_provider: str = "gemini" # memo synthesis: 'gemini' | 'ollama'
                                         # set to 'gemini' to preserve writing quality
                                         # while agents use ollama for tool calls

    # Pinecone
    pinecone_api_key: str = Field(default="")
    pinecone_index_name: str = Field(default="quanta-terminal")

    # News
    news_api_key: str = Field(default="")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Supabase / DB
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="", validation_alias="SUPABASE_KEY")
    supabase_jwt_secret: str = Field(default="")   # Settings > API > JWT Secret
    database_url: str = Field(default="")

    # App
    app_env: str = Field(default="development")
    secret_key: str = Field(default="change-me")

    # Sentry
    sentry_dsn: str = Field(default="")   # leave blank to disable

    # Tracked stocks
    tracked_tickers_raw: str = Field(
        default="QUBT,RGTI,QBTS,IONQ,NVDA,SMCI,MSTR,ARQQ",
        validation_alias="TRACKED_TICKERS",
    )

    @property
    def tracked_tickers(self) -> List[str]:
        return [t.strip().upper() for t in self.tracked_tickers_raw.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
