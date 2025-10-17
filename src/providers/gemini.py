"""Google Gemini provider implementation."""
import time
import logging
from typing import Optional, Callable, Type, TypeVar, cast
from google import genai
from google.genai import types
from pydantic import BaseModel

from src.models import PerformanceMetrics
from src.config import settings
from .base import (
    BaseProvider,
    ProviderError,
    RateLimitError,
    ModelUnavailableError,
    APITimeoutError
)

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini API provider - auto-loads API key from settings."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize Gemini provider.

        Args:
            model: Model name to use (defaults to settings.gemini_model)
        """
        api_key = settings.gemini_api_key
        model = model or settings.gemini_model
        super().__init__(api_key, model)
        # Initialize client once and reuse it
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def name(self) -> str:
        return "gemini"

    def generate_structured(self, prompt: str, response_model: Type[T]) -> T:
        """Generate structured output using Pydantic model schema."""
        try:
            if not self._client:
                raise ProviderError("Gemini client not initialized")
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_model,
                    temperature=settings.validation_temperature,
                    max_output_tokens=settings.validation_max_tokens
                )
            )

            if response.parsed is None:
                raise ProviderError("Gemini returned empty structured response")

            # Cast to the expected type T 
            return cast(T, response.parsed)

        except Exception as e:
            raise ProviderError(f"Gemini structured generation error: {str(e)}")

    def _invoke_model(
        self,
        prompt: str,
        code: str,
        metrics: PerformanceMetrics,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Call Gemini API with streaming and error handling."""
        try:
            if not self._client:
                raise ProviderError("Gemini client not initialized")

            # Single prompt with code included
            full_prompt = f"{prompt}\n\nCode to explain:\n\n{code}"

            first_token_time = None
            explanation = ""
            final_chunk = None

            # Use generate_content_stream for streaming
            response = self._client.models.generate_content_stream(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=settings.explanation_temperature,
                    max_output_tokens=settings.explanation_max_tokens
                )
            )

            for chunk in response:
                if first_token_time is None and chunk.text:
                    first_token_time = time.time()
                    metrics.time_to_first_token = first_token_time - metrics.start_time

                if chunk.text:
                    explanation += chunk.text
                    # Call the stream callback if provided
                    if stream_callback:
                        stream_callback(chunk.text)

                # Keep track of the last chunk
                final_chunk = chunk

            # Get usage metadata from the final chunk
            if final_chunk and hasattr(final_chunk, 'usage_metadata'):
                usage = final_chunk.usage_metadata
                if usage and hasattr(usage, 'total_token_count'):
                    metrics.total_tokens = usage.total_token_count

            if not explanation:
                raise ProviderError("Gemini returned empty response")

            return explanation

        except Exception as e:
            error_msg = str(e).lower()

            # Check for rate limiting
            if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                raise RateLimitError(f"Gemini rate limit exceeded: {str(e)}")

            # Check for timeout
            elif "timeout" in error_msg or "timed out" in error_msg:
                raise APITimeoutError(f"Gemini API timeout: {str(e)}")

            # Check for model availability
            elif "not found" in error_msg or "invalid model" in error_msg or "404" in error_msg:
                raise ModelUnavailableError(f"Gemini model '{self.model}' not available: {str(e)}")

            # Check for authentication issues
            elif "unauthorized" in error_msg or "invalid api key" in error_msg or "401" in error_msg or "403" in error_msg:
                raise ProviderError(f"Gemini authentication failed. Check your GEMINI_API_KEY: {str(e)}")

            # Generic error
            else:
                raise ProviderError(f"Gemini API error: {str(e)}")
