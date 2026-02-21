"""
Parameter Optimizer Module - Smart parameter search using binary search.

This is where the intelligence happens! Instead of brute-force testing every
combination, we use sequential binary search to efficiently find optimal
parameters:

1. Set turdsize based on noise analysis (not searched - just chosen)
2. Binary search for optimal threshold (coarse adjustment - gets shapes right)
3. Binary search for optimal smooth (fine adjustment - tweaks curve details)

This approach exploits the fact that these parameters affect ORTHOGONAL aspects
of the output - threshold determines WHERE shapes are, smooth determines HOW
they're represented. So we can optimize them independently!
"""
from pathlib import Path
from typing import Dict, Tuple, Callable, Optional, List
from dataclasses import dataclass, field

from . import log_info, log_debug, log_section, create_progress_bar
from . import config


# ============================================================================
# Data Classes for Clean Parameter Handling
# ============================================================================

@dataclass
class OptimizationResult:
    """Results from parameter optimization."""
    best_threshold: float
    best_smooth: float
    turdsize: int
    opttolerance: float
    turnpolicy: str
    best_score: float
    threshold_iterations: int
    smooth_iterations: int
    total_evaluations: int


@dataclass
class SearchBounds:
    """Min and max values for binary search."""
    min_val: float
    max_val: float
    
    def contains(self, value: float) -> bool:
        """Check if value is within bounds."""
        return self.min_val <= value <= self.max_val
    
    def clamp(self, value: float) -> float:
        """Clamp value to bounds."""
        return max(self.min_val, min(self.max_val, value))


# ============================================================================
# Binary Search Implementation
# ============================================================================

def binary_search_parameter(
    evaluate_func: Callable[[float], float],
    initial_value: float,
    bounds: SearchBounds,
    initial_step: float,
    min_step: float,
    min_improvement: float,
    param_name: str,
    temp_dir: Optional[Path] = None
) -> Tuple[float, float, int]:
    """
    Binary search for optimal parameter value.
    
    This is the core optimization algorithm! It works by:
    1. Try current value → score it
    2. Try stepping up and down → score both
    3. Move toward whichever improved score
    4. If neither improved → we're at a peak, halve step size
    5. Repeat until steps get tiny or improvements get negligible
    
    Args:
        evaluate_func: Function that takes a parameter value and returns SSIM score
        initial_value: Where to start searching
        bounds: Min and max allowed values
        initial_step: How big to make first steps
        min_step: Stop when step size gets this small
        min_improvement: Stop when score gains are smaller than this
        param_name: For logging (e.g., "threshold" or "smooth")
        temp_dir: Optional temp directory for saving test results (for VisualLogger)
        
    Returns:
        Tuple of (best_value, best_score, iterations_taken)
    """
    log_section(f"Binary Search: {param_name}")
    log_info(f"Starting at {initial_value:.3f}, step={initial_step:.3f}")
    
    best_value = initial_value
    best_score = evaluate_func(best_value)
    step_size = initial_step
    iterations = 0
    
    log_info(f"Initial score: {best_score:.4f}")
    
    with create_progress_bar(f"Optimizing {param_name}") as progress:
        # We don't know exactly how many iterations, so make it indeterminate
        task = progress.add_task(f"[cyan]{param_name}", total=None)
        
        while step_size >= min_step:
            iterations += 1
            progress.update(task, advance=1)
            
            # Try both directions
            value_lower = bounds.clamp(best_value - step_size)
            value_higher = bounds.clamp(best_value + step_size)
            
            # Skip if we're at a boundary and can't move that direction
            score_lower = None
            score_higher = None
            
            if value_lower != best_value:  # Can actually move lower
                score_lower = evaluate_func(value_lower)
                log_debug(f"  Try {value_lower:.3f} → {score_lower:.4f}")
            
            if value_higher != best_value:  # Can actually move higher
                score_higher = evaluate_func(value_higher)
                log_debug(f"  Try {value_higher:.3f} → {score_higher:.4f}")
            
            # Find best direction
            improved = False
            
            if score_lower is not None and score_lower > best_score + min_improvement:
                # Lower is better!
                improvement = score_lower - best_score
                best_value = value_lower
                best_score = score_lower
                improved = True
                log_info(f"  ↓ Improved to {best_value:.3f} (score={best_score:.4f}, +{improvement:.4f})")
                
            elif score_higher is not None and score_higher > best_score + min_improvement:
                # Higher is better!
                improvement = score_higher - best_score
                best_value = value_higher
                best_score = score_higher
                improved = True
                log_info(f"  ↑ Improved to {best_value:.3f} (score={best_score:.4f}, +{improvement:.4f})")
            
            if not improved:
                # Neither direction helped → we're at a local peak
                # Halve the step size and try finer adjustments
                step_size /= 2
                log_debug(f"  Peaked! Halving step to {step_size:.4f}")
                
                # If step is now too small, we're done
                if step_size < min_step:
                    log_info(f"  Step size below threshold ({min_step:.4f}), stopping")
                    break
    
    log_info(f"Converged after {iterations} iterations")
    log_info(f"Best {param_name}: {best_value:.3f} (score={best_score:.4f})")
    
    return best_value, best_score, iterations


# ============================================================================
# Main Optimizer Class
# ============================================================================

class ParameterOptimizer:
    """
    Orchestrates the sequential parameter optimization process.
    
    This class brings together all the pieces:
    - Image analysis (to set turdsize and initial threshold)
    - Binary search (to find optimal threshold and smooth)
    - Score evaluation (to guide the search)
    - History tracking (to create visual comparison sheets!)
    """
    
    def __init__(self, score_function: Callable[[Dict], float]):
        """
        Initialize the optimizer.
        
        Args:
            score_function: Function that takes parameter dict and returns SSIM score
                          Example: {'threshold': 0.45, 'smooth': 1.0, 'turdsize': 2}
                          Returns: 0.9234
        """
        self.score_function = score_function
        log_debug("ParameterOptimizer initialized")
    
    def determine_turdsize(self, noise_level: str) -> int:
        """
        Set turdsize (speckle removal) based on image noise analysis.
        
        This isn't optimized - it's just chosen based on analysis!
        
        Args:
            noise_level: "low", "moderate", or "high"
            
        Returns:
            Appropriate turdsize value
        """
        if noise_level == "low":
            turdsize = config.TURDSIZE_LOW_NOISE
        elif noise_level == "moderate":
            turdsize = config.TURDSIZE_MODERATE_NOISE
        else:  # high
            turdsize = config.TURDSIZE_HIGH_NOISE
        
        log_info(f"Set turdsize={turdsize} based on {noise_level} noise level")
        return turdsize
    
    def optimize(self, image_analysis: Dict) -> OptimizationResult:
        """
        Run the full sequential optimization process.
        
        This is the main entry point! It:
        1. Determines turdsize from noise analysis
        2. Binary searches threshold (coarse adjustment)
        3. Binary searches smooth (fine adjustment)
        4. Returns best parameters found + full history!
        
        Args:
            image_analysis: Dict from image_analysis.analyze_image()
                          Contains: noise_level, background_type, etc.
                          
        Returns:
            OptimizationResult with best parameters, scores, AND evaluation history
        """
        log_section("Sequential Parameter Optimization")
        
        # Step 1: Set turdsize based on noise (not searched!)
        turdsize = self.determine_turdsize(image_analysis['noise_level'])
        
        # Always use max optimization and default turn policy
        opttolerance = config.POTRACE_DEFAULTS['opttolerance']
        turnpolicy = config.POTRACE_DEFAULTS['turnpolicy']
        
        total_evals = 0
        
        # ====================================================================
        # Phase 1: Optimize threshold (COARSE - gets shapes right)
        # ====================================================================
        
        # Choose starting point and bounds based on background
        if image_analysis['background_type'] == 'light':
            initial_threshold = config.THRESHOLD_INITIAL_LIGHT_BG
            threshold_bounds = SearchBounds(*config.THRESHOLD_BOUNDS_LIGHT_BG)
        else:  # dark
            initial_threshold = config.THRESHOLD_INITIAL_DARK_BG
            threshold_bounds = SearchBounds(*config.THRESHOLD_BOUNDS_DARK_BG)
        
        # Create evaluation function for threshold
        # This captures turdsize and opttolerance, varies threshold
        def eval_threshold(threshold_val: float) -> float:
            params = {
                'blacklevel': threshold_val,
                'turdsize': turdsize,
                'alphamax': 1.0,  # Use default smooth during threshold search
                'opttolerance': opttolerance,
                'turnpolicy': turnpolicy,
            }
            return self.score_function(params)
        
        # Binary search for best threshold
        best_threshold, score_after_threshold, threshold_iters = binary_search_parameter(
            evaluate_func=eval_threshold,
            initial_value=initial_threshold,
            bounds=threshold_bounds,
            initial_step=config.THRESHOLD_STEP_INITIAL,
            min_step=config.THRESHOLD_MIN_STEP,
            min_improvement=config.THRESHOLD_MIN_IMPROVEMENT,
            param_name="threshold"
        )
        
        total_evals += threshold_iters
        
        # ====================================================================
        # Phase 2: Optimize smooth (FINE - tweaks curve details)
        # ====================================================================
        
        # Now threshold is locked in, optimize smoothness
        smooth_bounds = SearchBounds(*config.SMOOTH_BOUNDS)
        
        def eval_smooth(smooth_val: float) -> float:
            params = {
                'blacklevel': best_threshold,  # LOCKED from Phase 1!
                'turdsize': turdsize,
                'alphamax': smooth_val,
                'opttolerance': opttolerance,
                'turnpolicy': turnpolicy,
            }
            return self.score_function(params)
        
        # Binary search for best smooth
        best_smooth, best_score, smooth_iters = binary_search_parameter(
            evaluate_func=eval_smooth,
            initial_value=config.SMOOTH_INITIAL,
            bounds=smooth_bounds,
            initial_step=config.SMOOTH_STEP_INITIAL,
            min_step=config.SMOOTH_MIN_STEP,
            min_improvement=config.SMOOTH_MIN_IMPROVEMENT,
            param_name="smooth"
        )
        
        total_evals += smooth_iters
        
        # ====================================================================
        # Done! Package up results
        # ====================================================================
        
        log_section("Optimization Complete")
        log_info(f"Best threshold: {best_threshold:.3f}")
        log_info(f"Best smooth: {best_smooth:.3f}")
        log_info(f"Turdsize: {turdsize}")
        log_info(f"Final SSIM score: {best_score:.4f}")
        log_info(f"Total evaluations: {total_evals}")
        
        return OptimizationResult(
            best_threshold=best_threshold,
            best_smooth=best_smooth,
            turdsize=turdsize,
            opttolerance=opttolerance,
            turnpolicy=turnpolicy,
            best_score=best_score,
            threshold_iterations=threshold_iters,
            smooth_iterations=smooth_iters,
            total_evaluations=total_evals
        )