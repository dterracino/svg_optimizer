"""
CLI Module - Command-line argument parsing.

This module handles all CLI argument parsing and help text,
keeping __main__.py focused on application logic.
"""
import argparse
from pathlib import Path


def parse_arguments():
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
        """
    )
    
    # Required arguments
    parser.add_argument(
        'input',
        type=Path,
        help='Input raster image (PNG, JPG, etc.)'
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output SVG file path (default: input filename with .svg extension)'
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
    
    return parser.parse_args()
