"""CLI command handlers."""
from pathlib import Path
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from typing import Optional

from src.core import CodeExplainer
from .formatters import (
    console,
    display_metrics,
    display_code_panel,
    display_error,
    display_success,
    display_warning,
    display_info
)


def explain_file_command(
    explainer: CodeExplainer,
    file_path: str,
    language: str,
    output_file: Optional[str] = None,
    provider: Optional[str] = None,
    show_metrics: bool = True
) -> bool:
    """
    Explain a single file.

    Args:
        explainer: CodeExplainer instance
        file_path: Path to file to explain
        language: Programming language
        output_file: Optional output file path
        provider: Optional provider name
        show_metrics: Whether to display metrics

    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate file path
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            display_error("File Not Found", f"File does not exist: {file_path}")
            return False

        if not file_path_obj.is_file():
            display_error("Invalid Path", f"Path is not a file: {file_path}")
            return False

        # Check file size (warn if > 10MB)
        file_size = file_path_obj.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB
            display_warning(f"Large file ({file_size / 1024 / 1024:.1f}MB). This may take a while...")

        # Read source file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except UnicodeDecodeError:
            display_error("Encoding Error", f"Cannot read file (not a text file or wrong encoding): {file_path}")
            return False

        # Check if file is empty
        if not code.strip():
            display_error("Empty File", f"File is empty: {file_path}")
            return False

        # Display file info
        display_info(f"\nAnalyzing: {file_path}", bold=True)
        console.print(f"[cyan]Language:[/cyan] {language}")

        # Display original code
        console.print("\n[bold]Original Code:[/bold]")
        display_code_panel(code, language)

        # Stream explanation with live markdown updates
        console.print("\n[bold]Explanation:[/bold]")
        explanation_text = ""

        with Live(
            Panel(Markdown("_Waiting for response..._"), title="AI-Generated Explanation", border_style="green"),
            console=console,
            refresh_per_second=10, # How many times a screen is redrawn per second
        ) as live:
            def stream_callback(chunk: str):
                nonlocal explanation_text
                explanation_text += chunk
                # Update the screen
                live.update(Panel(Markdown(explanation_text), title="AI-Generated Explanation", border_style="green"))

            # Perform explanation with streaming
            result = explainer.explain(
                code=code,
                provider_name=provider,
                stream_callback=stream_callback
            )

        # Display metrics
        if show_metrics:
            console.print()
            display_metrics(result)

        # Save to output file if specified
        if output_file:
            _save_explanation_to_file(result, file_path, language, output_file)
            display_success(f"Explanation saved to: {output_file}")

        return True

    except KeyboardInterrupt:
        console.print()
        display_warning("Operation cancelled by user")
        return False
  
    except Exception as e:
        display_error("Error", str(e))
        return False


def explain_directory_command(
    explainer: CodeExplainer,
    input_dir: str,
    output_dir: str,
    language: str,
    pattern: str = "*",
    provider: Optional[str] = None
):
    """
    Explain multiple files in a directory.

    Args:
        explainer: CodeExplainer instance
        input_dir: Input directory path
        output_dir: Output directory path
        language: Programming language
        pattern: File pattern to match
        provider: Optional provider name
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Find all matching files based on the pattern user provided
    files = list(input_path.glob(pattern))

    if not files:
        display_warning(f"No files matching pattern '{pattern}' found in {input_dir}")
        return

    display_info(f"\nFound {len(files)} file(s) to explain", bold=True)

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for file_path in files:
        if file_path.is_file():
            # Generate output filename
            output_file = output_path / f"{file_path.stem}_explanation.md"

            # Explain file
            success = explain_file_command(
                explainer=explainer,
                file_path=str(file_path),
                language=language,
                output_file=str(output_file),
                provider=provider,
                show_metrics=False  # Don't show individual metrics for batch
            )

            if success:
                success_count += 1

    # Show summary
    display_info(f"\nSummary: {success_count}/{len(files)} files explained successfully", bold=True)


def list_providers_command(explainer: CodeExplainer):
    """
    List available providers.

    Args:
        explainer: CodeExplainer instance
    """
    available = explainer.list_available_providers()

    if not available:
        display_warning("No providers available. Please configure API keys in .env file for gemini setup and/or ensure ollama is running on your machine.")
        return

    display_info("\nAvailable Providers:", bold=True)
    for provider in available:
        display_success(provider)


def _save_explanation_to_file(result, file_path: str, language: str, output_file: str):
    """Save explanation to markdown file."""
    output_content = f"# Code Explanation\n\n"
    output_content += f"**File:** {file_path}\n\n"
    output_content += f"**Language:** {language}\n\n"
    output_content += f"## Original Code\n\n```{language.lower()}\n{result.original_code}\n```\n\n"
    output_content += f"## Explanation\n\n{result.explanation}\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
