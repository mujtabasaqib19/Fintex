"""
Application settings and configuration.
Uses pydantic-settings for environment variable management.
"""
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from pydantic import Field, AliasChoices
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: Optional[str] = Field(None, env="SUPABASE_SERVICE_KEY")
    
    # Qdrant Vector Database
    qdrant_url: str = Field(..., env="QDRANT_URL")
    qdrant_api_key: str = Field(..., env="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="snippets", env="QDRANT_COLLECTION")
    
    # Ollama (for embeddings)
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_embedding_model: str = Field(default="nomic-embed-text", env="OLLAMA_EMBEDDING_MODEL")
    
    # Google Gemini AI (for chat/reasoning only)
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    chat_model: str = "gemini-2.0-flash"
    chat_model_fallbacks: str = Field(
        default="gemini-2.0-flash,gemini-2.0-flash-lite,gemini-1.5-flash-002,gemini-1.5-flash",
        env="CHAT_MODEL_FALLBACKS",
    )
    embedding_model: str = "models/embedding-001"
    
    # External APIs
    psx_api_key: Optional[str] = Field(None, env="PSX_API_KEY")
    forex_api_key: Optional[str] = Field(None, env="FOREX_API_KEY")
    serpapi_api_key: Optional[str] = Field(None, env="SERPAPI_API_KEY")
    huggingface_api_key: Optional[str] = Field(
        None,
        validation_alias=AliasChoices(
            "HUGGINGFACE_API_KEY",
            "huggingface_api_key",
            "HF_TOKEN",
            "hf_token",
        ),
    )
    hf_chat_model: str = Field(default="Qwen/Qwen2.5-7B-Instruct", env="HF_CHAT_MODEL")
    hf_fallback_models: str = Field(
        default="meta-llama/Llama-3.1-8B-Instruct,HuggingFaceH4/zephyr-7b-beta,google/gemma-2-9b-it,mistralai/Mistral-7B-Instruct-v0.3",
        env="HF_FALLBACK_MODELS",
    )
    # HF's free serverless `hf-inference` provider deprecated chat-completion
    # routing for these open models, so requests 404 at router.huggingface.co.
    # Keep this OFF by default — Gemini is primary. Flip to true only if you
    # have an HF PRO / paid-provider token that can serve these models.
    hf_chat_enabled: bool = Field(default=False, env="HF_CHAT_ENABLED")
    
    # Processing
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens_per_request: int = 4000
    
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
