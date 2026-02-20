#!/usr/bin/env python3
"""
SVG Auto-Optimizer - Main CLI Application

This is the user-facing command-line tool that brings together all the modules
to automatically optimize bitmap-to-SVG conversion parameters.

Usage:
    python -m svg_optimizer input.png
    python -m svg_optimizer input.png --output custom.svg
    python -m svg_optimizer input.png --skip-optimization
"""
import sys
import argparse
from pathlib import Path
from typing import Optional
import time

# Import all our beautiful modules!
from svg_optimizer import (
    log_info, log_error, log_success, log_section, log_warning, log_debug
)
from svg_optimizer import config
from svg_optimizer.utils import (
    validate_input_file, validate_output_path, setup_logging
)
from svg_optimizer.image_analysis import analyze_image
from svg_optimizer.potrace_tracer import PotraceTracer
from svg_optimizer.inkscape_wrapper import InkscapeWrapper
from svg_optimizer.image_comparer import ImageComparer
from svg_optimizer.parameter_optimizer import ParameterOptimizer


# ============================================================================
# CLI Argument Parsing
# ============================================================================

def parse_arguments():
    """Parse command-line arguments with helpful descriptions."""
    parser = argparse.ArgumentParser(
        description="Automatically optimize bitmap-to-SVG conversion parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - optimize and save as input.svg
  %(prog)s logo.png
  
  # Specify custom output location
  %(prog)s logo.png --output my_logo.svg
  
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


# ============================================================================
# Main Application Logic
# ============================================================================

def main():
    """Main application entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging(log_file=args.log_file, verbose=args.verbose)
    
    # Welcome message!
    log_section("SVG Auto-Optimizer")
    log_info(f"Input: {args.input}")
    
    # ========================================================================
    # Step 1: Validate Inputs
    # ========================================================================
    
    if not validate_input_file(args.input):
        log_error("Invalid input file, exiting")
        return 1
    
    # Determine output paths
    if args.output:
        output_svg = args.output
    else:
        # Default: same name as input, but .svg
        output_svg = args.input.with_suffix(config.DEFAULT_OUTPUT_SUFFIX)
    
    if not validate_output_path(output_svg):
        log_error("Cannot write to output location, exiting")
        return 1
    
    log_info(f"Output: {output_svg}")
    
    # Comparison sheet path
    if args.no_comparison:
        comparison_path = None
        log_info("Comparison sheet: [disabled]")
    else:
        if args.comparison:
            comparison_path = args.comparison
        else:
            # Default: input_comparison.png
            comparison_path = args.input.with_stem(
                args.input.stem + config.DEFAULT_COMPARISON_SUFFIX.replace('.png', '')
            ).with_suffix('.png')
        log_info(f"Comparison sheet: {comparison_path}")
    
    # ========================================================================
    # Step 2: Analyze Image
    # ========================================================================
    
    try:
        image_info = analyze_image(args.input)
    except Exception as e:
        log_error(f"Image analysis failed: {e}")
        return 1
    
    # ========================================================================
    # Step 3: Initialize Components
    # ========================================================================
    
    log_section("Initializing Components")
    
    tracer = PotraceTracer()
    inkscape = InkscapeWrapper()
    
    # Validate Inkscape is available
    if not inkscape.validate():
        log_error("Inkscape not found or not working, cannot continue")
        return 1
    
    log_success("All components ready!")
    
    # ========================================================================
    # Step 4: Try Defaults First
    # ========================================================================
    
    log_section("Testing Default Parameters")
    
    start_time = time.time()
    
    # Build default parameters
    default_params = {
        'blacklevel': config.POTRACE_DEFAULTS['blacklevel'],
        'turdsize': config.POTRACE_DEFAULTS['turdsize'],
        'alphamax': config.POTRACE_DEFAULTS['alphamax'],
        'opttolerance': config.POTRACE_DEFAULTS['opttolerance'],
    }
    
    # Allow manual threshold override
    if args.threshold is not None:
        default_params['blacklevel'] = args.threshold
        log_info(f"Using manual threshold override: {args.threshold:.3f}")
    
    log_info(f"Default parameters: threshold={default_params['blacklevel']:.3f}, "
             f"turdsize={default_params['turdsize']}, "
             f"smooth={default_params['alphamax']:.2f}")
    
    # Trace with defaults
    svg_content_default = tracer.trace_to_svg_string(
        args.input,
        blacklevel=default_params['blacklevel'],
        turdsize=default_params['turdsize'],
        alphamax=default_params['alphamax'],
        opttolerance=default_params['opttolerance']
    )
    
    if svg_content_default is None:
        log_error("Failed to trace with default parameters")
        return 1
    
    # Score the defaults
    with ImageComparer(inkscape) as comparer:
        default_score = comparer.compare_svg_string_to_original(
            args.input,
            svg_content_default
        )
    
    log_info(f"Default SSIM score: {default_score:.4f}")
    
    # Check if defaults are good enough
    if default_score >= config.SSIM_GOOD_ENOUGH_THRESHOLD or args.skip_optimization:
        if default_score >= config.SSIM_GOOD_ENOUGH_THRESHOLD:
            log_success(f"Score {default_score:.4f} exceeds threshold "
                       f"({config.SSIM_GOOD_ENOUGH_THRESHOLD:.2f}) - defaults are great!")
        else:
            log_info("Skipping optimization as requested")
        
        # Save the default SVG
        with open(output_svg, 'w', encoding='utf-8') as f:
            f.write(svg_content_default)
        
        elapsed = time.time() - start_time
        
        log_section("Complete!")
        log_success(f"Saved SVG: {output_svg}")
        log_info(f"Final score: {default_score:.4f}")
        log_info(f"Time: {elapsed:.1f}s")
        
        return 0
    
    # ========================================================================
    # Step 5: Optimize Parameters
    # ========================================================================
    
    log_warning(f"Score {default_score:.4f} below threshold "
                f"({config.SSIM_GOOD_ENOUGH_THRESHOLD:.2f})")
    log_info("Starting parameter optimization...")
    
    # Create score function for optimizer
    # This is a closure that captures the necessary context
    def score_params(params: dict) -> float:
        """Score function for parameter optimization."""
        svg = tracer.trace_to_svg_string(
            args.input,
            blacklevel=params['blacklevel'],
            turdsize=params['turdsize'],
            alphamax=params['alphamax'],
            opttolerance=params['opttolerance']
        )
        
        if svg is None:
            return 0.0
        
        with ImageComparer(inkscape) as comparer:
            score = comparer.compare_svg_string_to_original(args.input, svg)
        
        return score
    
    # Run optimization!
    optimizer = ParameterOptimizer(score_function=score_params)
    result = optimizer.optimize(image_info)
    
    # ========================================================================
    # Step 6: Generate Final SVG
    # ========================================================================
    
    log_section("Generating Final SVG")
    
    success = tracer.trace_to_svg(
        args.input,
        output_svg,
        blacklevel=result.best_threshold,
        turdsize=result.turdsize,
        alphamax=result.best_smooth,
        opttolerance=result.opttolerance
    )
    
    if not success:
        log_error("Failed to generate final SVG")
        return 1
    
    # ========================================================================
    # Step 7: Summary
    # ========================================================================
    
    elapsed = time.time() - start_time
    
    log_section("Optimization Complete!")
    log_success(f"Saved SVG: {output_svg}")
    log_info(f"Final parameters:")
    log_info(f"  Threshold: {result.best_threshold:.3f}")
    log_info(f"  Smooth: {result.best_smooth:.2f}")
    log_info(f"  Turdsize: {result.turdsize}")
    log_info(f"Final SSIM score: {result.best_score:.4f}")
    log_info(f"Improvement: {result.best_score - default_score:+.4f}")
    log_info(f"Total evaluations: {result.total_evaluations}")
    log_info(f"Time: {elapsed:.1f}s")
    
    return 0


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == '__main__':
    sys.exit(main())
