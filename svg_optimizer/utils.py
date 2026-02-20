"""
Utility functions and unified logging system.

This module provides the DRY-compliant logging that outputs to BOTH
the Python logger (for file logging) AND Rich console (for pretty output).

Key principle: One call, two outputs. Never duplicate logging statements!
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from . import config


# ============================================================================
# Rich Console Setup (for pretty output)
# ============================================================================
console = Console()


# ============================================================================
# Python Logger Setup (for file logging)
# ============================================================================
def setup_logging(log_file: Optional[Path] = None, verbose: bool = False):
    """
    Set up Python's logging system.
    
    Args:
        log_file: Path to log file. If None, logs to svg_optimizer.log in current dir
        verbose: If True, set log level to DEBUG instead of INFO
    """
    if log_file is None:
        log_file = Path.cwd() / config.LOG_FILE_NAME
    
    level = logging.DEBUG if verbose else getattr(logging, config.LOG_LEVEL)
    
    logging.basicConfig(
        level=level,
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            # Don't add StreamHandler - we use Rich for console output
        ]
    )
    
    return logging.getLogger('svg_optimizer')


# Global logger instance
_logger = None

def get_logger():
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


# ============================================================================
# Unified Logging Functions (DRY magic happens here!)
# ============================================================================

def log_info(message: str, style: Optional[str] = None):
    """
    Log an info message to BOTH file logger and Rich console.
    
    Args:
        message: The message to log
        style: Optional Rich style (e.g., "green", "bold blue", "cyan")
    """
    logger = get_logger()
    logger.info(message)
    
    if style:
        console.print(f"[{style}]{message}[/{style}]")
    else:
        console.print(message)


def log_warning(message: str):
    """Log a warning to BOTH file logger and Rich console (yellow)."""
    logger = get_logger()
    logger.warning(message)
    console.print(f"[yellow]⚠ {message}[/yellow]")


def log_error(message: str):
    """Log an error to BOTH file logger and Rich console (red)."""
    logger = get_logger()
    logger.error(message)
    console.print(f"[bold red]✗ {message}[/bold red]")


def log_success(message: str):
    """Log a success message to BOTH file logger and Rich console (green)."""
    logger = get_logger()
    logger.info(f"SUCCESS: {message}")
    console.print(f"[bold green]✓ {message}[/bold green]")


def log_debug(message: str):
    """Log a debug message to file logger only (not shown in console)."""
    logger = get_logger()
    logger.debug(message)


def log_section(title: str):
    """
    Log a section header for better organization.
    
    Args:
        title: Section title
    """
    logger = get_logger()
    separator = "=" * 60
    logger.info(f"\n{separator}\n{title}\n{separator}")
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("[cyan]" + "─" * 60 + "[/cyan]")


# ============================================================================
# Progress Bar Helpers
# ============================================================================

def create_progress_bar(description: str = "Processing"):
    """
    Create a Rich progress bar for long-running operations.
    
    Args:
        description: Description text shown next to progress bar
        
    Returns:
        Progress object (use with context manager)
        
    Example:
        with create_progress_bar("Optimizing") as progress:
            task = progress.add_task(description, total=100)
            for i in range(100):
                # do work
                progress.update(task, advance=1)
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


# ============================================================================
# Path Validation Helpers
# ============================================================================

def validate_input_file(file_path: Path) -> bool:
    """
    Validate that an input file exists and is readable.
    
    Args:
        file_path: Path to input file
        
    Returns:
        True if valid, False otherwise (logs error if invalid)
    """
    if not file_path.exists():
        log_error(f"Input file does not exist: {file_path}")
        return False
    
    if not file_path.is_file():
        log_error(f"Input path is not a file: {file_path}")
        return False
    
    # Try to read it
    try:
        with open(file_path, 'rb') as f:
            f.read(1)  # Just read one byte to check readability
        return True
    except PermissionError:
        log_error(f"Permission denied reading file: {file_path}")
        return False
    except Exception as e:
        log_error(f"Error accessing file {file_path}: {e}")
        return False


def validate_output_path(file_path: Path) -> bool:
    """
    Validate that an output file path is writable.
    
    Args:
        file_path: Path to output file
        
    Returns:
        True if valid, False otherwise (logs error if invalid)
    """
    # Check if parent directory exists
    parent = file_path.parent
    if not parent.exists():
        log_error(f"Output directory does not exist: {parent}")
        return False
    
    # Check if we can write to parent directory
    if not parent.is_dir():
        log_error(f"Output parent path is not a directory: {parent}")
        return False
    
    # If file exists, check if we can overwrite it
    if file_path.exists():
        try:
            with open(file_path, 'a') as f:
                pass  # Just check write permission
            return True
        except PermissionError:
            log_error(f"Permission denied writing to file: {file_path}")
            return False
    else:
        # File doesn't exist, check if we can create it
        try:
            file_path.touch()
            file_path.unlink()  # Clean up test file
            return True
        except PermissionError:
            log_error(f"Permission denied creating file: {file_path}")
            return False
        except Exception as e:
            log_error(f"Error creating file {file_path}: {e}")
            return False


def validate_external_tool(tool_path: Path, tool_name: str) -> bool:
    """
    Validate that an external tool (like Inkscape) exists and is executable.
    
    Args:
        tool_path: Path to the tool executable
        tool_name: Human-readable name for logging
        
    Returns:
        True if valid, False otherwise
    """
    if not tool_path.exists():
        log_error(f"{tool_name} not found at: {tool_path}")
        log_info(f"Please ensure {tool_name} is installed correctly", style="yellow")
        return False
    
    if not tool_path.is_file():
        log_error(f"{tool_name} path is not a file: {tool_path}")
        return False
    
    log_debug(f"Found {tool_name} at: {tool_path}")
    return True
