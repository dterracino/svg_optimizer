"""
CLI Module - Command-line argument parsing.

This module handles all CLI argument parsing and help text,
keeping __main__.py focused on application logic.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .svg_border import BORDER_UNITS


def _positive_distance(value: str) -> float:
    """Parse a finite positive distance in the selected border units."""
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def _smoothing_distance(value: str) -> float:
    """Parse a finite nonnegative smoothing radius."""
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    return number


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments with helpful descriptions.
    
    Returns:
        Namespace object with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Automatically optimize bitmap-to-SVG conversion parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - optimize and save as input.svg
  %(prog)s logo.png
  
  # Specify custom output location
  %(prog)s logo.png --output my_logo.svg
  
  # AI upscale before tracing (improves quality for low-res images)
  %(prog)s logo.png --upscale
  
  # Upscale with specific method and 4x factor
  %(prog)s logo.png --upscale --upscale-method realesrgan --upscale-factor 4
  
  # Upscale with custom denoise level (waifu2x only)
  %(prog)s noisy.png --upscale --upscale-method waifu2x --upscale-denoise 2
  
  # Skip optimization, just use defaults
  %(prog)s logo.png --skip-optimization
  
  # Save comparison sheet to custom location
  %(prog)s logo.png --comparison logo_comparison.png
  
  # Skip the comparison sheet entirely
  %(prog)s logo.png --no-comparison
  
  # Verbose debug output
  %(prog)s logo.png --verbose

  # Add a vector-only border to existing SVG artwork
  %(prog)s logo.svg --border-offset 5 --border-smoothing 10
        """
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    # Required arguments
    parser.add_argument(
        'input',
        type=Path,
        help='Input raster image, or existing SVG with --border or --border-offset'
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output SVG path (default: input_border_TYPE_SIZEUNIT.svg with border, input.svg otherwise)'
    )
    
    parser.add_argument(
        '-c', '--comparison',
        type=Path,
        help='Comparison sheet PNG path (default: input_comparison.png)'
    )
    
    parser.add_argument(
        '--no-comparison',
        action='store_true',
        help='Skip generating the visual comparison sheet'
    )
    
    # Optimization control
    parser.add_argument(
        '--skip-optimization',
        action='store_true',
        help='Skip parameter optimization, just use defaults (fast!)'
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        help='Override: Set specific threshold value (0.0-1.0)'
    )
    
    # Image preprocessing options
    parser.add_argument(
        '--upscale',
        action='store_true',
        help='Enable AI upscaling before tracing (improves edge quality)'
    )
    
    parser.add_argument(
        '--upscale-method',
        type=str,
        choices=['realesrgan', 'waifu2x', 'auto'],
        default='auto',
        help='AI upscaling method (default: auto - tries Real-ESRGAN first)'
    )
    
    parser.add_argument(
        '--upscale-factor',
        type=int,
        choices=[2, 4],
        default=2,
        help='Upscaling factor: 2x or 4x (default: 2)'
    )
    
    parser.add_argument(
        '--upscale-denoise',
        type=int,
        choices=[0, 1, 2, 3],
        default=None,
        help='Denoise level for waifu2x: 0=none, 1=light, 2=medium, 3=heavy (default: 0)'
    )
    
    border = parser.add_argument_group("Vector border (distances in --border-units)")
    border.add_argument(
        "--border-type", "--border-style", choices=("outline", "frame"),
        help="Border shape: outline (default), or bounding-box frame"
    )
    border.add_argument(
        "--corner-radius", type=_smoothing_distance,
        help="Frame centerline corner radius in --border-units (default: 0, square)"
    )
    border.add_argument(
        "--border", action="store_true",
        help="Add a vector border with scale-aware defaults for omitted distances"
    )
    border.add_argument(
        "--border-units", choices=BORDER_UNITS,
        help="Units for all explicit border distances; percent uses the shorter canvas side "
             "(default: svg)"
    )
    border.add_argument(
        "--border-offset", type=_positive_distance,
        help="Add an enclosing vector border with this minimum clearance from artwork"
    )
    border.add_argument(
        "--border-smoothing", type=_smoothing_distance,
        help="Gaussian perimeter averaging distance; 0 keeps a tight cubic fit "
             "(default: automatic SVG scale)"
    )
    border.add_argument(
        "--border-tolerance", type=_positive_distance,
        help="Maximum vector curve-flattening error (default: automatic SVG scale)"
    )
    border.add_argument(
        "--border-width", type=_positive_distance,
        help="Border stroke width (default: automatic SVG scale)"
    )
    border.add_argument(
        "--border-color",
        help="Border stroke color: SVG color name or #RGB/#RRGGBB (default: black)"
    )

    # Logging options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose debug output'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        help='Custom log file path (default: svg_optimizer.log)'
    )
    
    arguments = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(arguments)
    border_enabled = args.border or args.border_offset is not None
    if not border_enabled and any(
        value is not None for value in
        (args.border_smoothing, args.border_tolerance, args.border_width, args.border_color,
         args.border_units, args.border_type, args.corner_radius)
    ):
        parser.error("border styling options require --border or --border-offset")
    if args.input.suffix.lower() == ".svg":
        if not border_enabled:
            parser.error("existing SVG input requires --border or --border-offset")
        raster_options = (
            "--upscale", "--upscale-method", "--upscale-factor", "--upscale-denoise",
            "--threshold", "--skip-optimization", "--comparison", "-c",
        )
        if args.comparison is not None or any(
            option.startswith(argument.split("=", 1)[0])
            for argument in arguments if argument.startswith("--") and argument != "--"
            for option in raster_options
        ):
            parser.error("raster tracing and comparison options cannot be used with SVG input")
    if args.output and args.output.suffix.lower() != ".svg" and border_enabled:
        parser.error("border output must have an .svg extension")
    if args.border_color is None:
        args.border_color = "black"
    if args.border_units is None:
        args.border_units = "svg"
    if args.border_type is None:
        args.border_type = "outline"
    if args.corner_radius is not None and args.border_type != "frame":
        parser.error("--corner-radius requires --border-type frame")
    if args.border_type == "frame" and args.border_smoothing is not None:
        parser.error("--border-smoothing applies only to outline borders; use --corner-radius")
    return args
