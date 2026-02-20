"""
Image Comparer Module - Quality scoring for SVG optimization.

This module handles the critical task of scoring how well an SVG matches
the original image. We use SSIM (Structural Similarity Index) with binary
thresholding to compare SHAPES rather than colors.

Why binary comparison? Because we're converting to B&W line art for CAD
tools like Fusion 360 - we care if the PATHS match, not if the colors match!
"""
from pathlib import Path
from typing import Tuple, Optional
import tempfile

from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

from . import log_debug, log_info, log_error
from . import config
from .inkscape_wrapper import InkscapeWrapper


# ============================================================================
# Image Comparer Class
# ============================================================================

class ImageComparer:
    """
    Scores SVG quality by comparing rasterized output to original image.
    
    The workflow:
    1. Rasterize SVG to PNG (using Inkscape)
    2. Load both original and rasterized images
    3. Convert both to binary (pure black/white)
    4. Calculate SSIM on the binary images
    5. Higher score = better match!
    """
    
    def __init__(self, inkscape_wrapper: Optional[InkscapeWrapper] = None):
        """
        Initialize the comparer.
        
        Args:
            inkscape_wrapper: InkscapeWrapper instance (creates one if None)
        """
        self.inkscape = inkscape_wrapper or InkscapeWrapper()
        self._temp_dir = None
        log_debug("ImageComparer initialized")
    
    def _get_temp_dir(self) -> Path:
        """Get or create temporary directory for rasterized PNGs."""
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix=config.TEMP_DIR_PREFIX))
            log_debug(f"Created temp directory: {self._temp_dir}")
        return self._temp_dir
    
    def cleanup_temp(self):
        """Clean up temporary files."""
        if self._temp_dir and self._temp_dir.exists():
            import shutil
            shutil.rmtree(self._temp_dir)
            log_debug(f"Cleaned up temp directory: {self._temp_dir}")
            self._temp_dir = None
    
    def calculate_ssim_binary(
        self,
        image1_path: Path,
        image2_path: Path,
        threshold: float = 0.5
    ) -> float:
        """
        Calculate SSIM between two images using binary (B/W) comparison.
        
        This is the KEY to fair comparison! We threshold both images to pure
        black and white before comparing, so we're measuring SHAPE similarity
        rather than color/luminance differences.
        
        Args:
            image1_path: First image (usually the original)
            image2_path: Second image (usually rasterized SVG)
            threshold: Binarization threshold (0.0-1.0)
                      Pixels below this → black, above → white
                      
        Returns:
            SSIM score (0.0-1.0, higher = better match)
        """
        # Load images as grayscale
        try:
            img1 = Image.open(image1_path).convert('L')
            img2 = Image.open(image2_path).convert('L')
        except Exception as e:
            log_error(f"Failed to load images for comparison: {e}")
            return 0.0
        
        # Check dimensions match
        if img1.size != img2.size:
            log_error(f"Image size mismatch: {img1.size} vs {img2.size}")
            return 0.0
        
        # Convert to numpy arrays
        arr1 = np.array(img1, dtype=np.float32)
        arr2 = np.array(img2, dtype=np.float32)
        
        # Threshold to pure binary (0 or 255)
        # This is where the magic happens! Now we're comparing shapes, not grays
        threshold_value = threshold * 255
        arr1_binary = np.where(arr1 < threshold_value, 0, 255).astype(np.uint8)
        arr2_binary = np.where(arr2 < threshold_value, 0, 255).astype(np.uint8)
        
        log_debug(f"Binarized images at threshold {threshold:.2f}")
        
        # Calculate SSIM on binary images
        # data_range=255 because pixel values are 0-255
        # full=False means return only the score (not the full diff image)
        score_value = ssim(arr1_binary, arr2_binary, data_range=255, full=False)
        
        # Type safety for Pylance
        assert isinstance(score_value, (float, np.floating)), "SSIM should return scalar"
        
        return float(score_value)
    
    def compare_svg_to_original(
        self,
        original_path: Path,
        svg_path: Path,
        comparison_threshold: float = 0.5
    ) -> float:
        """
        Compare an SVG file to its original raster image.
        
        This is the main entry point for quality scoring!
        
        Workflow:
        1. Load original to get dimensions
        2. Rasterize SVG to PNG at those same dimensions
        3. Run binary SSIM comparison
        4. Return score
        
        Args:
            original_path: Original raster image
            svg_path: SVG file to evaluate
            comparison_threshold: Binary threshold for SSIM (0.0-1.0)
            
        Returns:
            SSIM score (0.0-1.0, higher = better)
        """
        log_debug(f"Comparing {svg_path.name} to original")
        
        # Get original image dimensions
        try:
            with Image.open(original_path) as img:
                width, height = img.size
        except Exception as e:
            log_error(f"Failed to read original image: {e}")
            return 0.0
        
        # Rasterize the SVG to a temp PNG
        temp_dir = self._get_temp_dir()
        temp_png = temp_dir / f"raster_{svg_path.stem}.png"
        
        if not self.inkscape.rasterize(svg_path, temp_png, width=width, height=height):
            log_error("Failed to rasterize SVG for comparison")
            return 0.0
        
        # Compare using binary SSIM
        score = self.calculate_ssim_binary(original_path, temp_png, threshold=comparison_threshold)
        
        log_debug(f"SSIM score: {score:.4f}")
        
        return score
    
    def compare_svg_string_to_original(
        self,
        original_path: Path,
        svg_content: str,
        comparison_threshold: float = 0.5
    ) -> float:
        """
        Compare SVG content (string) to original image.
        
        This is used in the optimization loop where we're generating
        SVGs on the fly without saving them to disk first.
        
        Args:
            original_path: Original raster image
            svg_content: SVG as a string
            comparison_threshold: Binary threshold for SSIM
            
        Returns:
            SSIM score (0.0-1.0)
        """
        log_debug("Comparing SVG string to original")
        
        # Get original dimensions
        try:
            with Image.open(original_path) as img:
                width, height = img.size
        except Exception as e:
            log_error(f"Failed to read original image: {e}")
            return 0.0
        
        # Rasterize from string
        temp_dir = self._get_temp_dir()
        temp_png = temp_dir / f"raster_{id(svg_content)}.png"
        
        if not self.inkscape.rasterize_from_string(
            svg_content, temp_png, width=width, height=height, temp_dir=temp_dir
        ):
            log_error("Failed to rasterize SVG string for comparison")
            return 0.0
        
        # Compare
        score = self.calculate_ssim_binary(original_path, temp_png, threshold=comparison_threshold)
        
        # Clean up this specific temp file (keep dir for reuse)
        if temp_png.exists():
            temp_png.unlink()
        
        return score
    
    def __enter__(self):
        """Context manager entry - for 'with' statement."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto cleanup."""
        self.cleanup_temp()
        return False  # Don't suppress exceptions
