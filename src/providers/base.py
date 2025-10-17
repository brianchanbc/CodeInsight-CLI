"""Base provider class and exceptions."""
from abc import ABC, abstractmethod
from typing import Optional, Callable, TypeVar, Type
from pydantic import BaseModel
from src.models import PerformanceMetrics
from src.prompts import get_explanation_prompt

# Generic type to be used for passing pydantic schema to generate structured output
T = TypeVar('T', bound=BaseModel) 


# ============================================================================
# Custom Exceptions
# ============================================================================

class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class RateLimitError(ProviderError):
    """Raised when API rate limit is exceeded."""
    pass


class ModelUnavailableError(ProviderError):
    """Raised when the model is not available."""
    pass


class APITimeoutError(ProviderError):
    """Raised when API request times out."""
    pass


# ============================================================================
# Base Provider Class
# ============================================================================

class BaseProvider(ABC):
    """Abstract base class for ML providers."""

    def __init__(self, api_key: Optional[str] = None, model: str = ""):
        """Initialize provider with API key and model."""
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    def _invoke_model(
        self,
        prompt: str,
        code: str,
        metrics: PerformanceMetrics,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Invoke model call and return explanation. Must be implemented by subclasses."""
        pass

    def is_available(self) -> bool:
        """Check if provider is available (has valid API key)."""
        return bool(self.api_key and len(self.api_key) > 0)

    def _build_prompt(self) -> str:
        """Build the system/user prompt for code explanation."""
        return get_explanation_prompt()

    @abstractmethod
    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """
        Generate structured output using Pydantic model.
        """
        pass

    def explain_code(
        self,
        code: str,
        metrics: PerformanceMetrics,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Build prompt and invoke model to explain code.
        """
        try:
            metrics.model = self.model
            metrics.model_provider = self.name

            prompt = self._build_prompt()
            explanation = self._invoke_model(prompt, code, metrics, stream_callback)

            return explanation.strip()

        except Exception as e:
            metrics.error = str(e)
            raise
