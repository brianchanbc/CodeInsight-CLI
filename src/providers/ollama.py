"""Ollama local LLM provider implementation."""
import time
import logging
from typing import Optional, Callable, Type, TypeVar
import ollama
from pydantic import BaseModel

from src.models import PerformanceMetrics
from src.config import settings
from .base import (
    BaseProvider,
    ProviderError,
    ModelUnavailableError,
    APITimeoutError
)

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider using official ollama package."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize Ollama provider.

        Args:
            model: Model name to use (defaults to settings.ollama_model)
        """
        model = model or settings.ollama_model
        # Ollama doesn't need an API key for local use
        super().__init__(api_key="local", model=model)
        # Cache availability check result
        self._is_available_cache: Optional[bool] = None

    @property
    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        """Check if Ollama is available by trying to list models (cached)."""
        if self._is_available_cache is not None:
            return self._is_available_cache

        try:
            ollama.list()
            self._is_available_cache = True
            return True
        except Exception:
            self._is_available_cache = False
            return False

    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """Generate structured output using Pydantic model schema."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format=response_model.model_json_schema(),
                options={
                    "temperature": settings.validation_temperature,
                    "num_predict": settings.validation_max_tokens
                }
            )

            # Parse the JSON response into the Pydantic model
            content = response.message.content
            if not content:
                raise ProviderError("Ollama returned empty structured response")

            result = response_model.model_validate_json(content)
            return result

        except Exception as e:
            raise ProviderError(f"Ollama structured generation error: {str(e)}")

    def _invoke_model(
        self,
        prompt: str,
        code: str,
        metrics: PerformanceMetrics,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Call Ollama API using ollama.chat() with error handling."""
        first_token_time = None
        explanation = ""

        try:
            # Use chat API with streaming
            stream = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': f"{prompt}\n\nCode to explain:\n\n{code}"
                }],
                stream=True,
                options={
                    "temperature": settings.explanation_temperature,
                    "num_predict": settings.explanation_max_tokens
                }
            )

            for chunk in stream:
                if first_token_time is None and chunk.get('message', {}).get('content'):
                    first_token_time = time.time()
                    metrics.time_to_first_token = first_token_time - metrics.start_time

                content = chunk.get('message', {}).get('content', '')
                if content:
                    explanation += content
                    # Call the stream callback if provided
                    if stream_callback:
                        stream_callback(content)

                # Extract metrics from final chunk if available
                if chunk.get('done'):
                    prompt_tokens = chunk.get('prompt_eval_count', 0)
                    completion_tokens = chunk.get('eval_count', 0)
                    metrics.total_tokens = prompt_tokens + completion_tokens

            if not explanation:
                raise ProviderError("Ollama returned empty response")

            return explanation

        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for connection issues
            if "connection" in error_msg or "refused" in error_msg or "unreachable" in error_msg:
                raise ProviderError(f"Cannot connect to Ollama server. Is it running? Try: ollama serve")

            # Check for model not found
            elif "model" in error_msg and ("not found" in error_msg or "pull" in error_msg):
                raise ModelUnavailableError(f"Ollama model '{self.model}' not found. Try: ollama pull {self.model}")

            # Check for timeout
            elif "timeout" in error_msg or "timed out" in error_msg:
                raise APITimeoutError(f"Ollama request timed out: {str(e)}")

            # Generic error
            else:
                raise ProviderError(f"Ollama error: {str(e)}")
