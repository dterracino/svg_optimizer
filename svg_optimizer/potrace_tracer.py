"""
Potrace Tracer Module - Bitmap to SVG conversion using potracer library.

This module handles all interaction with the potracer library, converting
bitmap images to SVG paths with configurable parameters.

Key responsibilities:
- Load images and prepare bitmaps for tracing
- Execute potrace tracing with specified parameters
- Convert potrace path lists to SVG strings
"""
from pathlib import Path
from typing import Dict, Optional
from io import StringIO

from PIL import Image
import numpy as np

# Import potrace - the pure Python potrace implementation
# Note: Package is 'potracer' but you import 'potrace' (no 'r')
try:
    from potrace import Bitmap
except ImportError as e:
    raise ImportError(
        "potrace library not found! Install it with: pip install potracer"
    ) from e

from . import log_debug, log_info, log_error
from . import config


# ============================================================================
# SVG Generation Helpers
# ============================================================================

def paths_to_svg(paths, width: int, height: int) -> str:
    """
    Convert potracer path to SVG string.
    
    Potracer returns a Path object that is iterable, containing Curve objects.
    Each Curve has segments which can be either BezierSegment or CornerSegment.
    
    All curves are combined into a SINGLE <path> element, with each curve
    being a separate sub-path (closed with Z).
    
    Args:
        paths: Path object from bitmap.trace()
        width: Image width (for viewBox)
        height: Image height (for viewBox)
        
    Returns:
        Complete SVG string
    """
    svg = StringIO()
    
    # SVG header with viewBox
    svg.write(f'<?xml version="1.0" standalone="no"?>\n')
    svg.write(f'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
              f'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n')
    svg.write(f'<svg width="{width}" height="{height}" '
              f'viewBox="0 0 {width} {height}" '
              f'xmlns="http://www.w3.org/2000/svg" version="1.1">\n')
    
    # ONE path element containing ALL curves
    svg.write('<path d="')
    
    # Each curve becomes a sub-path within this single path element
    for curve in paths:
        # Start at the curve's start point
        start = curve.start_point
        svg.write(f'M{start.x:.2f},{start.y:.2f} ')
        
        # Iterate through segments in the curve
        for segment in curve.segments:
            if segment.is_corner:
                # Corner segment - line to the corner point, then to end
                svg.write(f'L{segment.c.x:.2f},{segment.c.y:.2f} ')
                svg.write(f'L{segment.end_point.x:.2f},{segment.end_point.y:.2f} ')
            else:
                # Bezier segment - cubic bezier curve
                svg.write(f'C{segment.c1.x:.2f},{segment.c1.y:.2f} '
                         f'{segment.c2.x:.2f},{segment.c2.y:.2f} '
                         f'{segment.end_point.x:.2f},{segment.end_point.y:.2f} ')
        
        # Close this sub-path
        svg.write('Z ')
    
    # Close the single path element
    svg.write('" fill="black" stroke="none"/>\n')
    svg.write('</svg>\n')
    
    return svg.getvalue()


# ============================================================================
# Main Tracer Class
# ============================================================================

class PotraceTracer:
    """
    Wrapper around potracer library for clean, DRY bitmap tracing.
    
    This class handles all the potrace-specific stuff so other modules
    don't need to know about Bitmap objects, path lists, etc.
    """
    
    def __init__(self):
        """Initialize the tracer."""
        log_debug("PotraceTracer initialized")
    
    def load_bitmap(self, image_path: Path, blacklevel: float = 0.5) -> Bitmap:
        """
        Load an image and convert to a Bitmap for tracing.
        
        This handles color→grayscale→binary conversion. The blacklevel
        determines what counts as "black" (part of the shape) vs "white"
        (background).
        
        Args:
            image_path: Path to input image
            blacklevel: Threshold for binarization (0.0-1.0)
                       Pixels darker than this become black, lighter become white
                       
        Returns:
            Bitmap object ready for tracing
            
        Raises:
            ValueError: If image cannot be loaded
        """
        log_debug(f"Loading bitmap from {image_path} with blacklevel={blacklevel:.3f}")
        
        # Load image and convert to grayscale
        try:
            img = Image.open(image_path).convert('L')
        except Exception as e:
            raise ValueError(f"Failed to load image {image_path}: {e}")
        
        # Get dimensions from PIL Image
        width, height = img.size  # PIL uses (width, height) order
        
        # Create Bitmap object
        # The Bitmap constructor handles the thresholding internally
        # based on the blacklevel we provide
        bitmap = Bitmap(img, blacklevel=blacklevel)
        
        log_debug(f"Created bitmap: {width}x{height} pixels")
        
        return bitmap
    
    def trace_bitmap(
        self,
        bitmap: Bitmap,
        turdsize: int = 2,
        alphamax: float = 1.0,
        opttolerance: float = 0.2,
    ) -> list:
        """
        Trace a bitmap to vector paths using potrace algorithm.
        
        This is where the actual magic happens! Potrace analyzes the bitmap
        and generates smooth bezier curves that follow the edges.
        
        Args:
            bitmap: Bitmap object to trace (from load_bitmap)
            turdsize: Suppress speckles up to this size (pixels)
                     Higher = more aggressive noise removal
            alphamax: Corner threshold parameter (0.0-1.34)
                     Lower = sharper corners, Higher = smoother curves
            opttolerance: Curve optimization tolerance (0.0-5.0)
                         Higher = join more segments (simpler paths)
                       
        Returns:
            List of Path objects (potrace internal format)
        """
        log_debug(f"Tracing with params: turdsize={turdsize}, "
                 f"alphamax={alphamax:.2f}, opttolerance={opttolerance:.2f}")
        
        # The actual tracing happens here!
        # bitmap.trace() returns a list of Path objects
        # Note: turnpolicy is an integer (4 = minority policy, which is the default)
        # opticurve=True means "use curve optimization" (always want this!)
        paths = bitmap.trace(
            turdsize=turdsize,
            turnpolicy=4,  # 4 = minority (default, best for most cases)
            alphamax=alphamax,
            opticurve=True,  # Enable curve optimization
            opttolerance=opttolerance
        )
        
        log_debug(f"Traced {len(paths)} paths")
        
        return paths
    
    def trace_to_svg(
        self,
        image_path: Path,
        output_path: Path,
        blacklevel: float = 0.5,
        turdsize: int = 2,
        alphamax: float = 1.0,
        opttolerance: float = 0.2
    ) -> bool:
        """
        Complete workflow: Load image → Trace → Save SVG.
        
        This is the high-level "just do it" method that handles everything.
        
        Args:
            image_path: Input raster image
            output_path: Where to save SVG
            blacklevel: Threshold for binarization (0.0-1.0)
            turdsize: Speckle suppression size
            alphamax: Corner smoothness (0.0-1.34)
            opttolerance: Curve optimization (0.0-5.0)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load and prepare bitmap
            bitmap = self.load_bitmap(image_path, blacklevel=blacklevel)
            
            # Trace to paths
            paths = self.trace_bitmap(
                bitmap,
                turdsize=turdsize,
                alphamax=alphamax,
                opttolerance=opttolerance
            )
            
            # Get dimensions from bitmap data
            height, width = bitmap.data.shape
            
            # Convert paths to SVG string
            svg_content = paths_to_svg(paths, width, height)
            
            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            log_debug(f"Saved SVG to {output_path}")
            return True
            
        except Exception as e:
            log_error(f"Tracing failed: {e}")
            return False
    
    def trace_to_svg_string(
        self,
        image_path: Path,
        blacklevel: float = 0.5,
        turdsize: int = 2,
        alphamax: float = 1.0,
        opttolerance: float = 0.2
    ) -> Optional[str]:
        """
        Trace image and return SVG as string (don't save to file).
        
        Useful for optimization loop where we want to compare results
        without creating a bunch of temp files.
        
        Args:
            Same as trace_to_svg (minus turnpolicy which is hardcoded)
            
        Returns:
            SVG content as string, or None if tracing failed
        """
        try:
            bitmap = self.load_bitmap(image_path, blacklevel=blacklevel)
            paths = self.trace_bitmap(
                bitmap,
                turdsize=turdsize,
                alphamax=alphamax,
                opttolerance=opttolerance
            )
            # Get dimensions from bitmap
            height, width = bitmap.data.shape
            svg_content = paths_to_svg(paths, width, height)
            return svg_content
            
        except Exception as e:
            log_error(f"Tracing to string failed: {e}")
            return None