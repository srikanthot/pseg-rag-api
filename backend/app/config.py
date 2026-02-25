import os
from functools import lru_cache
from typing import Optional

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure OpenAI - Chat
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_deployment: str

    # Azure OpenAI - Embedding (falls back to chat endpoint/key if not set)
    azure_openai_embedding_endpoint: Optional[str] = None
    azure_openai_embedding_api_key: Optional[str] = None
    azure_openai_embedding_deployment: str

    # Azure AI Search
    azure_search_endpoint: str
    azure_search_api_key: str
    azure_search_index_name: str = "rag-documents"

    # Azure Blob Storage (for SAS URL generation on citations)
    azure_storage_connection_string: str
    azure_storage_container_name: str = "pdfs"

    # RAG
    top_k: int = 5

    @field_validator("azure_openai_endpoint", "azure_search_endpoint")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("azure_openai_embedding_endpoint")
    @classmethod
    def strip_embedding_slash(cls, v: Optional[str]) -> Optional[str]:
        return v.rstrip("/") if v else v

    def get_embedding_endpoint(self) -> str:
        return self.azure_openai_embedding_endpoint or self.azure_openai_endpoint

    def get_embedding_api_key(self) -> str:
        return self.azure_openai_embedding_api_key or self.azure_openai_api_key

    model_config = ConfigDict(
        env_file=[".env", "../.env"],  # works whether run from project root or parent
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore old/unknown env vars (e.g. SCORE_THRESHOLD, LOG_LEVEL)
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
