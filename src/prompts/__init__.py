"""Centralized prompt templates for the application."""

from .prompts import (
    CODE_EXPLANATION_PROMPT,
    CODE_VALIDATION_PROMPT,
    get_validation_prompt,
    get_explanation_prompt
)

__all__ = [
    "CODE_EXPLANATION_PROMPT",
    "CODE_VALIDATION_PROMPT",
    "get_validation_prompt",
    "get_explanation_prompt"
]
