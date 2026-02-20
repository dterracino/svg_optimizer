#!/usr/bin/env python3
"""
SSIM Tester - Simple script to compare an original image with its SVG conversion.

WORKFLOW:
1. You manually convert an image to SVG in Inkscape with your desired settings
2. This script rasterizes the SVG back to PNG at original dimensions
3. Calculates SSIM score between original and rasterized SVG
4. Repeat with different settings to find your "good enough" threshold

This helps us empirically determine what SSIM score means "success"!
"""
import sys
import argparse
from pathlib import Path
import subprocess

from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

from svg_optimizer import log_info, log_error, log_success, log_section, log_debug
from svg_optimizer.config import INKSCAPE_PATH


def rasterize_svg_with_inkscape(svg_path: Path, output_png: Path, width: int, height: int) -> bool:
    """
    Use Inkscape to convert SVG back to PNG at specific dimensions.
    
    Args:
        svg_path: Path to SVG file
        output_png: Where to save the PNG
        width: Target width in pixels
        height: Target height in pixels
        
    Returns:
        True if successful, False otherwise
    """
    cmd = [
        str(INKSCAPE_PATH),
        str(svg_path),
        '--export-type=png',
        f'--export-filename={output_png}',
        f'--export-width={width}',
        f'--export-height={height}',
    ]
    
    try:
        log_info(f"Rasterizing SVG to {width}x{height}...", style="cyan")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        log_success(f"Created rasterized PNG: {output_png}")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Inkscape failed: {e.stderr}")
        return False
    except FileNotFoundError:
        log_error(f"Inkscape not found at: {INKSCAPE_PATH}")
        log_error("Please update INKSCAPE_PATH in config.py")
        return False


def calculate_ssim(image1_path: Path, image2_path: Path, threshold: float = 0.5) -> float:
    """
    Calculate SSIM between two images using binary (black/white) comparison.
    
    This ensures we're comparing SHAPES (edges/paths) rather than color values,
    which is what matters for SVG line art going into tools like Fusion 360.
    
    Args:
        image1_path: Path to first image (original)
        image2_path: Path to second image (SVG rasterized)
        threshold: Threshold for binarization (0.0-1.0, default 0.5)
                   Pixels below this become black, above become white
        
    Returns:
        SSIM score (0.0 to 1.0, higher is better)
    """
    # Load images and convert to grayscale first
    img1 = Image.open(image1_path).convert('L')
    img2 = Image.open(image2_path).convert('L')
    
    # Ensure same dimensions
    if img1.size != img2.size:
        log_error(f"Image dimensions don't match: {img1.size} vs {img2.size}")
        return 0.0
    
    # Convert to numpy arrays
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)
    
    # Threshold to pure binary (0 or 255)
    # This is the key! Now we're comparing black/white shapes, not gray values
    threshold_value = threshold * 255
    arr1_binary = np.where(arr1 < threshold_value, 0, 255).astype(np.uint8)
    arr2_binary = np.where(arr2 < threshold_value, 0, 255).astype(np.uint8)
    
    log_debug(f"Binarized images at threshold {threshold:.2f}")
    
    # Calculate SSIM on binary images
    # data_range=255 because we're working with 0-255 pixel values
    # full=False means we only get the score, not the full diff image
    score_value = ssim(arr1_binary, arr2_binary, data_range=255, full=False)
    
    # Type assertion for Pylance - we know this is a float because full=False
    assert isinstance(score_value, (float, np.floating)), "SSIM should return a scalar"
    
    return float(score_value)


def main():
    parser = argparse.ArgumentParser(
        description="Test SSIM score between original image and SVG conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLE WORKFLOW:
  1. Manually convert my_logo.png to my_logo.svg in Inkscape
  2. Run: python ssim_tester.py my_logo.png my_logo.svg
  3. See the SSIM score
  4. Try different Inkscape settings and repeat
  5. Determine what SSIM value looks "good enough" to you
        """
    )
    parser.add_argument('original', type=Path, help='Original raster image (PNG/JPG)')
    parser.add_argument('svg', type=Path, help='SVG file you created in Inkscape')
    parser.add_argument('--keep-temp', action='store_true', 
                       help='Keep temporary rasterized PNG file')
    
    args = parser.parse_args()
    
    # Validate inputs
    log_section("SSIM Comparison Test")
    
    if not args.original.exists():
        log_error(f"Original image not found: {args.original}")
        return 1
    
    if not args.svg.exists():
        log_error(f"SVG file not found: {args.svg}")
        return 1
    
    # Get original image dimensions
    try:
        with Image.open(args.original) as img:
            width, height = img.size
        log_info(f"Original image: {width}x{height} pixels")
    except Exception as e:
        log_error(f"Failed to read original image: {e}")
        return 1
    
    # Rasterize the SVG
    temp_png = args.svg.with_suffix('.temp_rasterized.png')
    
    if not rasterize_svg_with_inkscape(args.svg, temp_png, width, height):
        return 1
    
    # Calculate SSIM
    log_info("Calculating SSIM score...", style="cyan")
    try:
        score = calculate_ssim(args.original, temp_png)
        
        # Display results with color coding
        log_section("RESULTS")
        
        if score >= 0.95:
            style = "bold green"
            verdict = "EXCELLENT - This would skip optimization!"
        elif score >= 0.90:
            style = "green"
            verdict = "VERY GOOD - Likely acceptable"
        elif score >= 0.85:
            style = "yellow"
            verdict = "GOOD - Might want to optimize"
        elif score >= 0.80:
            style = "orange"
            verdict = "OK - Should definitely optimize"
        else:
            style = "red"
            verdict = "POOR - Needs optimization"
        
        log_info(f"SSIM Score: {score:.4f}", style=style)
        log_info(f"Assessment: {verdict}", style=style)
        
        # Educational info
        print()
        log_info("Score Guide:", style="cyan")
        log_info("  0.95+ = Excellent (would skip optimization)")
        log_info("  0.90-0.95 = Very good")
        log_info("  0.85-0.90 = Good")  
        log_info("  0.80-0.85 = OK")
        log_info("  <0.80 = Poor")
        
    except Exception as e:
        log_error(f"SSIM calculation failed: {e}")
        return 1
    finally:
        # Cleanup
        if not args.keep_temp and temp_png.exists():
            temp_png.unlink()
            log_info("Cleaned up temporary files", style="dim")
        elif args.keep_temp:
            log_info(f"Kept temporary file: {temp_png}", style="dim")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())