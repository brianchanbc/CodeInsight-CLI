#!/usr/bin/env python3
"""Command-line interface for code explanation tool."""
import argparse
import logging
import sys
from pathlib import Path

from src.core import CodeExplainer
from src.cli import (
    explain_file_command,
    explain_directory_command,
    list_providers_command,
    display_error
)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ML-powered code explanation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Explain a single file
  python cli.py explain -i script.py -l Python

  # Explain and save to file
  python cli.py explain -i code.js -l JavaScript -o explanation.md

  # Explain multiple files
  python cli.py explain -i ./src -o ./explanations -l Python --pattern "*.py"

  # Use specific provider
  python cli.py explain -i code.py -l Python --provider gemini

  # Check available providers
  python cli.py providers
        """
    )

    # Create subparsers that enable subcommands (e.g. explain, providers)
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Providers command
    subparsers.add_parser("providers", help="List available providers")

    # Explain command
    explain_parser = subparsers.add_parser("explain", help="Explain code")
    explain_parser.add_argument("-i", "--input", required=True, help="Input file or directory")
    explain_parser.add_argument("-l", "--language", required=True, help="Programming language")
    explain_parser.add_argument("-o", "--output", help="Output file or directory")
    explain_parser.add_argument("--pattern", default="*", help="File pattern for directory input (default: *)")
    explain_parser.add_argument("--provider", choices=["gemini", "ollama"], help="ML provider to use")
    explain_parser.add_argument("--no-metrics", action="store_true", help="Don't show metrics")

    args = parser.parse_args()

    # Initialize explainer 
    try:
        explainer = CodeExplainer()
    except Exception as e:
        display_error("Initialization Failed", str(e))
        sys.exit(1)

    if args.command == "explain":
        # Handle explain command
        input_path = Path(args.input)

        if input_path.is_file():
            # Single file explanation
            success = explain_file_command(
                explainer=explainer,
                file_path=args.input,
                language=args.language,
                output_file=args.output,
                provider=args.provider,
                show_metrics=not args.no_metrics
            )
            sys.exit(0 if success else 1)

        elif input_path.is_dir():
            # Directory explanation
            if not args.output:
                display_error("Missing Argument", "--output is required for directory input")
                sys.exit(1)

            explain_directory_command(
                explainer=explainer,
                input_dir=args.input,
                output_dir=args.output,
                language=args.language,
                pattern=args.pattern,
                provider=args.provider,
            )

        else:
            display_error("Invalid Path", f"Input path does not exist: {args.input}")
            sys.exit(1)

    elif args.command == "providers":
        # Handle providers command
        list_providers_command(explainer)

    else:
        # By default assume user needs help due to wrong command
        parser.print_help()


if __name__ == "__main__":
    main()
