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
from pathlib import Path
from typing import Optional
import time

from PIL import Image

# Import all our beautiful modules!
from svg_optimizer import (
    log_info, log_error, log_success, log_section, log_warning, log_debug
)
from svg_optimizer import config
from svg_optimizer.cli import parse_arguments
from svg_optimizer.utils import (
    validate_input_file, validate_output_path, setup_logging
)
from svg_optimizer.image_analysis import analyze_image
from svg_optimizer.potrace_tracer import PotraceTracer
from svg_optimizer.inkscape_wrapper import InkscapeWrapper
from svg_optimizer.image_comparer import ImageComparer
from svg_optimizer.parameter_optimizer import ParameterOptimizer
from svg_optimizer.upscalers import upscale_for_tracing


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
    comparison_path = None
    if not args.no_comparison:
        if args.comparison:
            comparison_path = args.comparison
        else:
            # Default: input_comparison.png
            comparison_path = args.input.with_stem(
                args.input.stem + config.DEFAULT_COMPARISON_SUFFIX.replace('.png', '')
            ).with_suffix('.png')
        log_info(f"Comparison sheet: {comparison_path}")
    else:
        log_info("Comparison sheet: [disabled]")
    
    # ========================================================================
    # Step 2: AI Upscaling (Optional)
    # ========================================================================
    
    # Track the actual input file to use for tracing (original or upscaled)
    working_input = args.input
    upscaled_temp_file = None
    
    if args.upscale:
        try:
            upscaled_path = upscale_for_tracing(
                args.input,
                method=args.upscale_method,
                scale=args.upscale_factor,
                denoise_level=args.upscale_denoise,
                output_path=None  # Will create temp file
            )
            
            if upscaled_path:
                working_input = upscaled_path
                upscaled_temp_file = upscaled_path  # Track for cleanup
                log_info(f"Using upscaled image for tracing: {upscaled_path}")
            else:
                log_warning("Upscaling failed, using original image")
                
        except ImportError as e:
            log_error(f"Upscaling dependencies not available: {e}")
            log_warning("Continuing with original image without upscaling")
            log_info("To enable upscaling, install: pip install -r requirements-gpu.txt")
        except Exception as e:
            log_error(f"Unexpected error during upscaling: {e}")
            log_warning("Continuing with original image")
    
    # ========================================================================
    # Step 3: Analyze Image
    # ========================================================================
    
    try:
        image_info = analyze_image(working_input)
    except Exception as e:
        log_error(f"Image analysis failed: {e}")
        return 1
    
    # ========================================================================
    # Step 4: Initialize Components
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
        working_input,
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
    temp_dir = None  # Initialize temp_dir in case we skip optimization
    
    if default_score >= config.SSIM_GOOD_ENOUGH_THRESHOLD or args.skip_optimization:
        if default_score >= config.SSIM_GOOD_ENOUGH_THRESHOLD:
            log_success(f"Score {default_score:.4f} exceeds threshold "
                       f"({config.SSIM_GOOD_ENOUGH_THRESHOLD:.2f}) - defaults are great!")
        else:
            log_info("Skipping optimization as requested")
        
        # Save the default SVG
        with open(output_svg, 'w', encoding='utf-8') as f:
            f.write(svg_content_default)
        
        # Cleanup upscaled temp file if it exists
        if upscaled_temp_file and upscaled_temp_file.exists():
            try:
                upscaled_temp_file.unlink()
                log_debug(f"Cleaned up upscaled temp file: {upscaled_temp_file}")
            except Exception as e:
                log_debug(f"Failed to cleanup upscaled temp file: {e}")
        
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
    
    # Create temp directory for saving test results (for VisualLogger later)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix=config.TEMP_DIR_PREFIX))
    log_info(f"Created temp directory: {temp_dir}")
    
    # Create ImageComparer that uses our temp directory (don't let it create its own!)
    comparer = ImageComparer(inkscape)
    comparer._temp_dir = temp_dir  # Share the temp directory
    
    evaluation_counter = [0]  # Use list so we can modify in closure
    
    # Create score function for optimizer
    # This is a closure that captures the necessary context
    def score_params(params: dict) -> float:
        """Score function for parameter optimization."""
        svg = tracer.trace_to_svg_string(
            working_input,
            blacklevel=params['blacklevel'],
            turdsize=params['turdsize'],
            alphamax=params['alphamax'],
            opttolerance=params['opttolerance']
        )
        
        if svg is None:
            return 0.0
        
        # Use the comparer directly (NOT with 'with' statement - we'll clean up manually later)
        score = comparer.compare_svg_string_to_original(args.input, svg)
        
        # Save this test to temp folder for VisualLogger!
        evaluation_counter[0] += 1
        test_id = f"test_{evaluation_counter[0]:03d}"
        
        # Save SVG
        svg_path = temp_dir / f"{test_id}{config.DEFAULT_OUTPUT_SUFFIX}"
        svg_path.write_text(svg, encoding='utf-8')
        
        # Save parameters and score
        import json
        params_path = temp_dir / f"{test_id}{config.DEFAULT_JSON_LOG_SUFFIX}"
        params_path.write_text(json.dumps({
            'params': params,
            'score': score,
            'test_id': test_id
        }, indent=2), encoding='utf-8')
        
        log_debug(f"Saved {test_id}: score={score:.4f}, threshold={params['blacklevel']:.3f}, smooth={params['alphamax']:.2f}")
        
        return score
    
    # Run optimization!
    optimizer = ParameterOptimizer(score_function=score_params)
    result = optimizer.optimize(image_info)
    
    # ========================================================================
    # Step 6: Generate Final SVG
    # ========================================================================
    
    log_section("Generating Final SVG")
    
    success = tracer.trace_to_svg(
        working_input,
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
    # Step 7: Generate Comparison Sheet (if requested)
    # ========================================================================
    
    if comparison_path and temp_dir.exists():
        log_section("Generating Comparison Sheet")
        
        from svg_optimizer.visual_logger import VisualLogger, ComparisonEntry
        import json
        
        # Load all the test results from temp folder
        entries = []
        search_pattern = f"test_*{config.DEFAULT_JSON_LOG_SUFFIX}"
        log_debug(f"Searching for: {temp_dir / search_pattern}")
        
        matching_files = list(temp_dir.glob(search_pattern))
        log_debug(f"Found {len(matching_files)} matching files")
        
        for params_file in sorted(matching_files):
            with open(params_file) as f:
                data = json.load(f)
            
            # Get the test_id from the params file (e.g., test_001.params.json -> test_001)
            # Remove the .params.json suffix to get just test_XXX
            test_base = params_file.name.replace(config.DEFAULT_JSON_LOG_SUFFIX, '')
            svg_file = params_file.parent / f"{test_base}{config.DEFAULT_OUTPUT_SUFFIX}"
            
            if svg_file.exists():
                svg_content = svg_file.read_text(encoding='utf-8')
                
                # Mark the winner (best score)
                is_winner = abs(data['score'] - result.best_score) < 0.0001
                
                entry = ComparisonEntry(
                    svg_content=svg_content,
                    params=data['params'],
                    score=data['score'],
                    is_winner=is_winner
                )
                entries.append(entry)
        
        if entries:
            logger = VisualLogger(inkscape)
            with Image.open(args.input) as img:
                orig_width = img.width
            
            success = logger.create_comparison_sheet(
                entries,
                comparison_path,
                args.input,
                target_width=orig_width
            )
            
            if success:
                log_success(f"Comparison sheet: {comparison_path}")
        else:
            log_warning("No test results found, skipping comparison sheet")
    
    # Cleanup comparer (but don't delete temp_dir yet - we still need it!)
    if 'comparer' in locals():
        comparer._temp_dir = None  # Prevent it from deleting our temp_dir
    
    # Cleanup temp directory
    if temp_dir and temp_dir.exists():
        if config.CLEANUP_TEMP_ON_SUCCESS:
            import shutil
            shutil.rmtree(temp_dir)
            log_debug(f"Cleaned up temp directory: {temp_dir}")
        else:
            log_info(f"Temp files kept at: {temp_dir}")
    
    # Cleanup upscaled temp file
    if upscaled_temp_file and upscaled_temp_file.exists():
        try:
            upscaled_temp_file.unlink()
            log_debug(f"Cleaned up upscaled temp file: {upscaled_temp_file}")
        except Exception as e:
            log_debug(f"Failed to cleanup upscaled temp file: {e}")
    
    # ========================================================================
    # Step 8: Summary
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