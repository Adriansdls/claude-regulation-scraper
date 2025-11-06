"""Configuration management."""

import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Config(BaseModel):
    """Global configuration."""

    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    semantic_scholar_api_key: Optional[str] = None

    # LLM Settings
    default_llm: str = "anthropic"  # anthropic or openai
    anthropic_model: str = "claude-3-7-sonnet-20250219"  # Updated to working model (Feb 2025)
    openai_model: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.1

    # Discovery Settings
    max_papers: int = 10000
    relevance_threshold: float = 0.6
    max_concurrent_requests: int = 10

    # Storage
    database_url: str = "sqlite:///./data/research_graph.db"
    redis_url: Optional[str] = None
    cache_enabled: bool = True

    # Paths
    data_dir: str = "./data"
    papers_dir: str = "./data/papers"
    graphs_dir: str = "./data/graphs"
    cache_dir: str = "./data/cache"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            default_llm=os.getenv("DEFAULT_LLM", "anthropic"),
            max_papers=int(os.getenv("MAX_PAPERS", "10000")),
            relevance_threshold=float(os.getenv("RELEVANCE_THRESHOLD", "0.6")),
            max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/research_graph.db"),
            redis_url=os.getenv("REDIS_URL"),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        )

    def validate_keys(self) -> bool:
        """Check if necessary API keys are set."""
        if self.default_llm == "anthropic" and not self.anthropic_api_key:
            return False
        if self.default_llm == "openai" and not self.openai_api_key:
            return False
        return True


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config():
    """Reset global config (useful for testing)."""
    global _config
    _config = None
