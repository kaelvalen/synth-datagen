"""SynthForge logging and console output utilities."""
from __future__ import annotations

import logging
import sys
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler

# Global console instance
console = Console()

# Configure logging
_log_handler: RichHandler | None = None


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """
    Configure logging for SynthForge.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
    
    Returns:
        Configured logger instance
    """
    global _log_handler
    
    logger = logging.getLogger("synthforge")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Rich console handler
    _log_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    _log_handler.setLevel(logging.DEBUG)
    logger.addHandler(_log_handler)
    
    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(file_handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get or create the SynthForge logger."""
    logger = logging.getLogger("synthforge")
    if not logger.handlers:
        setup_logging()
    return logger


# ── Progress Helpers ────────────────────────────────────────────────────────

def create_progress() -> Progress:
    """Create a Rich progress bar instance."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def create_spinner_progress() -> Progress:
    """Create a simple spinner progress for indeterminate tasks."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


# ── Output Helpers ──────────────────────────────────────────────────────────

def print_header(title: str, subtitle: str | None = None) -> None:
    """Print a styled header."""
    text = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        text += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(text, border_style="cyan"))


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def print_spec_table(spec: Any) -> None:
    """Print DataSpec as a formatted table."""
    table = Table(title=f"📋 {spec.name}", border_style="blue")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Type", spec.data_type.value)
    table.add_row("Rows", str(spec.row_count))
    table.add_row("Locale", spec.locale)
    table.add_row("Fields", str(len(spec.fields)))
    
    if spec.constraints:
        table.add_row("Constraints", ", ".join(spec.constraints[:3]))
    
    console.print(table)


def print_fields_table(fields: list) -> None:
    """Print field specifications as a table."""
    table = Table(title="📊 Fields", border_style="green")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Nullable", style="dim")
    table.add_column("Unique", style="dim")
    table.add_column("Range/Categories", style="white", max_width=30)
    
    for f in fields[:10]:  # Show first 10 fields
        range_info = ""
        if f.categories:
            range_info = f"[{', '.join(f.categories[:3])}{'...' if len(f.categories) > 3 else ''}]"
        elif f.min_val is not None or f.max_val is not None:
            range_info = f"{f.min_val or '∞'} – {f.max_val or '∞'}"
        
        table.add_row(
            f.name,
            f.dtype,
            "✓" if f.nullable else "✗",
            "✓" if f.unique else "✗",
            range_info,
        )
    
    if len(fields) > 10:
        table.add_row(f"... +{len(fields) - 10} more", "", "", "", "")
    
    console.print(table)


def print_validation_result(result: Any) -> None:
    """Print validation result with styling."""
    if result.passed:
        console.print(Panel(
            f"[bold green]✓ Validation Passed[/bold green]\n"
            f"Score: {result.score:.2%}",
            border_style="green",
        ))
    else:
        issues_text = "\n".join(f"• {i}" for i in result.issues[:5])
        if len(result.issues) > 5:
            issues_text += f"\n... +{len(result.issues) - 5} more"
        
        console.print(Panel(
            f"[bold yellow]⚠ Validation Issues[/bold yellow]\n"
            f"Score: {result.score:.2%}\n\n"
            f"[dim]{issues_text}[/dim]",
            border_style="yellow",
        ))


def print_result_summary(result: Any) -> None:
    """Print final pipeline result summary."""
    table = Table(title="📦 Generation Complete", border_style="cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Records", str(len(result.dataset.records)))
    table.add_row("Validation", f"{'✓ Passed' if result.validation.passed else '⚠ Issues'} ({result.validation.score:.2%})")
    table.add_row("Iterations", str(result.iterations))
    table.add_row("Output", result.export_path or "N/A")
    
    console.print(table)
