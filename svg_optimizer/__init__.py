"""
SVG Auto-Optimizer - Automatically optimize bitmap-to-SVG conversion parameters.

This package provides tools for converting raster images (line art, logos) to 
optimized SVG format by testing multiple parameter combinations and selecting
the best result based on visual similarity scoring.
"""

__version__ = "0.1.0"
__author__ = "Dave"

# Make key utilities easily importable
from .utils import (
    log_info,
    log_warning,
    log_error,
    log_success,
    log_debug,
    log_section,
    create_progress_bar,
)

__all__ = [
    'log_info',
    'log_warning', 
    'log_error',
    'log_success',
    'log_debug',
    'log_section',
    'create_progress_bar',
]