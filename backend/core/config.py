from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).parents[2] / ".env"
load_dotenv(_ROOT_ENV)


class Settings(BaseSettings):
    # LLM
    google_api_key: str = Field(default="")

    # LangSmith
    langchain_api_key: str = Field(default="")
    langchain_tracing: str = Field(default="true")
    langchain_project: str = Field(default="quanta-terminal")

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
    supabase_service_role_key: str = Field(default="")
    database_url: str = Field(default="")

    # App
    app_env: str = Field(default="development")
    secret_key: str = Field(default="change-me")

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
