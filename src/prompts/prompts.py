"""Prompt templates for code explanation and validation."""

# ============================================================================
# Code Explanation Prompt
# ============================================================================

CODE_EXPLANATION_PROMPT = """You are an expert programmer and technical educator. \
Analyze the following piece of code and provide a clear, comprehensive explanation. \
Focus on:
1. Overall purpose and functionality
2. Complex sections, algorithms, or patterns used
3. Key logic flow and important details
4. Potential edge cases or gotchas
5. Performance considerations if relevant

Structure your explanation to be clear and easy to understand. \
Use markdown formatting for readability."""


def get_explanation_prompt() -> str:
    """
    Get the code explanation prompt.

    Returns:
        The prompt string for code explanation
    """
    return CODE_EXPLANATION_PROMPT


# ============================================================================
# Code Validation Prompt
# ============================================================================

CODE_VALIDATION_PROMPT = """Validate if this is actual programming code.

Code to validate:
```
{code_sample}
```

Be lenient. 
Provide your assessment with a confidence score."""


def get_validation_prompt(code_sample: str) -> str:
    """
    Get the code validation prompt with the code sample inserted.

    Args:
        code_sample: The code snippet to validate

    Returns:
        The formatted validation prompt
    """
    return CODE_VALIDATION_PROMPT.format(code_sample=code_sample)
