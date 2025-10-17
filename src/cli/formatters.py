"""CLI output formatters using Rich library."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


console = Console()


def display_metrics(result):
    """Display performance metrics in a formatted table."""
    metrics = result.metrics

    table = Table(title="Performance Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Model Provider", metrics.model_provider)
    table.add_row("Model", metrics.model)

    # Show cache status 
    cache_status = "Yes ✓" if metrics.cache_hit else "No"
    table.add_row("Cache Hit", cache_status)

    if metrics.total_time:
        table.add_row("Total Time", f"{metrics.total_time:.3f}s")

    if metrics.time_to_first_token:
        table.add_row("Time to First Token", f"{metrics.time_to_first_token:.3f}s")

    if metrics.total_tokens:
        table.add_row("Total Tokens", str(metrics.total_tokens))

    if metrics.tokens_per_second:
        table.add_row("Tokens/Second", f"{metrics.tokens_per_second:.2f}")

    if metrics.error:
        table.add_row("Error", metrics.error, style="red")

    console.print(table)


def display_code_panel(code: str, language: str):
    """Display code in a syntax-highlighted panel."""
    syntax = Syntax(code, language.lower(), theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Code to Explain", border_style="blue"))


def display_error(title: str, message: str, suggestion: str = ""):
    """Display error message with optional suggestion."""
    console.print(f"\n[red]✗ {title}[/red]", style="bold red")
    console.print(f"{message}")
    if suggestion:
        console.print(f"\n[yellow]Suggestion:[/yellow] {suggestion}")


def display_success(message: str):
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def display_warning(message: str):
    """Display warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def display_info(message: str, bold: bool = False):
    """Display informational message."""
    if bold:
        console.print(f"[bold]{message}[/bold]")
    else:
        console.print(message)
