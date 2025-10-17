"""Main code explanation service."""
import time
import hashlib
import logging
from typing import Optional, List, Callable, cast
from diskcache import Cache
from src.models import ExplanationResult, PerformanceMetrics, ValidationResult
from src.providers import GeminiProvider, OllamaProvider, BaseProvider
from src.prompts import get_validation_prompt
from src.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Main CodeExplainer Class
# ============================================================================

class CodeExplainer:
    """Main code explanation service with provider management and fallback."""

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize explainer with providers.

        Providers auto-load API keys from environment variables:
        - Gemini: GEMINI_API_KEY
        - Ollama: No API key needed (local)

        Default: Gemini (free tier) with Ollama fallback

        Args:
            provider: Optional provider to use (defaults to settings.default_provider)
        """
        self.default_provider = provider or settings.default_provider
        self.use_cache = settings.cache_enabled
        self.cache_ttl = settings.cache_ttl
        self.providers = {
            "gemini": GeminiProvider(model=settings.gemini_model),
            "ollama": OllamaProvider(model=settings.ollama_model)
        }
        # Initialize disk cache
        if self.use_cache:
            self.cache = Cache(settings.cache_dir)

    def _get_provider(self, provider_name: Optional[str] = None) -> BaseProvider:
        """Get ML provider by name."""
        name = provider_name or self.default_provider
        if name not in self.providers:
            raise ValueError(f"Unknown provider: {name}")
        provider = self.providers[name]
        if not provider.is_available():
            raise ValueError(f"Provider {name} is not available (missing API key)")
        return provider

    def _get_fallback_provider(self, failed_provider: str) -> Optional[BaseProvider]:
        """
        Get fallback provider (the other provider).

        - gemini -> ollama
        - ollama -> gemini
        """
        # Get the other provider as fallback
        fallback_name = "ollama" if failed_provider == "gemini" else "gemini"
        provider = self.providers.get(fallback_name)

        if provider and provider.is_available():
            return provider

        return None

    def _get_cache_key(self, code: str, provider_name: str, model: str) -> str:
        """Generate cache key from code content, provider, and model."""
        cache_input = f"{code}|{provider_name}|{model}"
        return hashlib.sha256(cache_input.encode()).hexdigest()

    def _validate_input_code(self, code: str) -> ValidationResult:
        """
        Quick sanity check on input code using LLM validator.

        Validates:
        - Is this actual code or gibberish?
        - Does it contain suspicious patterns?
        - Is it reasonable to explain?
        - Basic size and structure checks

        Returns:
            ValidationResult with validation status and reason
        """
        # Quick heuristic checks first (no LLM needed)
        if len(code.strip()) < settings.min_code_length:
            return ValidationResult(
                is_valid=False,
                reason=f"Code is too short (minimum {settings.min_code_length} characters)",
                confidence=1.0
            )

        if len(code) > settings.max_code_length:
            return ValidationResult(
                is_valid=False,
                reason=f"Code is too large (maximum {settings.max_code_length // 1000}KB)",
                confidence=1.0
            )

        # Use LLM validator for deeper checks with structured output
        # Try Ollama first (local, fast), fall back to Gemini if needed
        validation_errors = []

        for provider_name in ["ollama", "gemini"]:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_available():
                continue

            try:
                # Limit code sample for validation
                code_sample = code[:settings.validation_sample_size]
                if len(code) > settings.validation_sample_size:
                    code_sample += "\n... (truncated)"

                # Get validation prompt from centralized location
                validation_prompt = get_validation_prompt(code_sample)

                # Use structured generation for reliable parsing
                result = provider.generate_structured(validation_prompt, ValidationResult)

                return result

            except Exception as e:
                validation_errors.append(f"{provider_name}: {str(e)}")
                # Continue to try next provider

        # If all validators fail, be permissive and allow the code through
        # (better to have false positives than false negatives)
        all_errors = "; ".join(validation_errors)
        return ValidationResult(
            is_valid=True,
            reason=f"Validation check skipped due to errors: {all_errors}",
            confidence=0.5
        )

    def explain(
        self,
        code: str,
        provider_name: Optional[str] = None,
        auto_fallback: bool = True,
        stream_callback: Optional[Callable[[str], None]] = None,
        validate_input: bool = True
    ) -> ExplanationResult:
        """
        Explain code using ML provider.

        Args:
            code: Source code to explain
            provider_name: Specific provider to use (uses default if None)
            auto_fallback: Whether to automatically fallback to another provider on failure
            stream_callback: Optional callback function called with each chunk of text
            validate_input: Whether to validate input code before explanation (default: True)

        Returns:
            ExplanationResult with explanation and metrics

        Raises:
            ValueError: If input validation fails
        """
        # Validate input code before processing
        if validate_input:
            validation_result = self._validate_input_code(code)
            if not validation_result.is_valid:
                raise ValueError(f"Input validation failed: {validation_result.reason}")

        # Try primary provider
        try:
            provider = self._get_provider(provider_name)
        except ValueError as e:
            if not auto_fallback:
                raise
            # Get the name of the provider that failed
            failed_provider_name = provider_name or self.default_provider
            fallback_provider = self._get_fallback_provider(failed_provider_name)
            if not fallback_provider:
                raise ValueError("No ML providers are available") from e
            provider = fallback_provider

        # Check cache first (skip validation for cached results)
        cache_key = None
        if self.use_cache:
            cache_key = self._get_cache_key(code, provider.name, provider.model)
            cache_start = time.time()
            cached_result = cast(Optional[ExplanationResult], self.cache.get(cache_key))
            if cached_result is not None:
                # Update metrics to reflect cache retrieval
                cached_result.metrics.cache_hit = True
                cached_result.metrics.start_time = cache_start
                cached_result.metrics.end_time = time.time()

                # If streaming callback provided, simulate streaming the cached explanation
                if stream_callback:
                    stream_callback(cached_result.explanation)
                return cached_result

        metrics = PerformanceMetrics(
            model=provider.model,
            model_provider=provider.name,
            start_time=time.time()
        )

        try:
            # Perform explanation
            explanation = provider.explain_code(code, metrics, stream_callback=stream_callback)
            metrics.end_time = time.time()

            result = ExplanationResult(
                original_code=code,
                explanation=explanation,
                metrics=metrics
            )

            # Save to cache with TTL
            if self.use_cache and cache_key:
                self.cache.set(cache_key, result, expire=self.cache_ttl)

            return result

        except Exception as e:
            metrics.end_time = time.time()
            metrics.error = str(e)

            # Try fallback if enabled
            if auto_fallback:
                fallback_provider = self._get_fallback_provider(provider.name)
                if fallback_provider:
                    return self.explain(
                        code,
                        provider_name=fallback_provider.name,
                        auto_fallback=False,
                        stream_callback=stream_callback,
                        validate_input=False  
                    )
            raise
    
    def list_available_providers(self) -> List[str]:
        """List available providers (those with valid API keys)."""
        return [
            name for name, provider in self.providers.items()
            if provider.is_available()
        ]
        