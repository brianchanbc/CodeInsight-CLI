"""Configuration management for the application."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Settings:
    """Application settings."""

    # API Keys (only thing that needs env var)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # Model Configuration
    default_provider: str = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    ollama_model: str = "llama3.2:1b"

    # Cache Configuration
    cache_enabled: bool = True
    cache_dir: str = ".cache"
    cache_ttl: int = 604800  # 7 days

    # Validation Configuration
    min_code_length: int = 10
    max_code_length: int = 100_000  # Maximum characters
    validation_sample_size: int = 1000 # First how many words for validation

    # Model Generation Configuration
    explanation_temperature: float = 0.7 # Higher to allow more flexibility
    explanation_max_tokens: int = 8192
    validation_temperature: float = 0.3 # Lower as we want more deterministic checks
    validation_max_tokens: int = 512

    # Logging Configuration
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
