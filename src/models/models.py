"""Data models for tracking metrics and results."""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


@dataclass
class PerformanceMetrics:
    """Tracks performance metrics for ML model calls."""
    model: str
    model_provider: str
    start_time: float
    end_time: Optional[float] = None
    time_to_first_token: Optional[float] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None
    cache_hit: bool = False

    @property
    def total_time(self) -> Optional[float]:
        """Calculate total execution time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def tokens_per_second(self) -> Optional[float]:
        """Calculate average tokens per second during generation (excludes initial latency)."""
        if self.end_time and self.time_to_first_token and self.total_tokens:
            # Calculate generation time: from first token to end
            first_token_time = self.start_time + self.time_to_first_token
            generation_time = self.end_time - first_token_time
            if generation_time > 0:
                return self.total_tokens / generation_time
        return None


@dataclass
class ExplanationResult:
    """Result of a code explanation operation."""
    original_code: str
    explanation: str
    metrics: PerformanceMetrics
    timestamp: datetime = field(default_factory=datetime.now)


class ValidationResult(BaseModel):
    """Result of input validation check (Pydantic model for structured output)."""
    is_valid: bool = Field(..., description="Whether the code is valid and safe to explain")
    reason: str = Field(..., description="Explanation of why the code is valid or invalid")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score between 0 and 1")