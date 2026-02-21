"""
Image Analysis Module - Noise detection and background characterization.

This module analyzes input images to determine:
1. Noise level (using Laplacian variance and residual analysis)
2. Background type (light vs dark)

These analyses help us intelligently select parameter ranges for optimization.
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, Tuple

from . import log_debug, log_info
from . import config


# ============================================================================
# Noise Analysis (ported from noise.py)
# ============================================================================

def compute_noise_metrics(image: np.ndarray) -> Dict[str, float]:
    """
    Compute noise-related metrics for line art images.
    
    Uses edge detection to separate signal (intentional lines) from noise
    (unwanted fuzz, grain, compression artifacts). For line art, edges ARE
    the content, so we mask them out and measure variation in the background.
    
    Args:
        image: Grayscale image as numpy array (uint8)
        
    Returns:
        Dict with keys:
            - laplacian_variance: High-frequency content (for reference)
            - residual_std: Noise in non-edge areas
            - noise_score: MAD of residual in non-edge areas
    """
    img = image.astype(np.float32)
    
    # 1) Laplacian variance (kept for reference, not used)
    laplacian = cv2.Laplacian(img, cv2.CV_32F)
    laplacian_variance = laplacian.var()
    
    # 2) Edge detection - find the intentional line art
    # Canny finds sharp edges (the actual lines we want to trace)
    edges = cv2.Canny(img.astype(np.uint8), 80, 160)
    non_edge_mask = edges == 0  # Everything that's NOT a line
    
    # 3) Measure noise only in non-edge areas
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    residual = img - blurred
    
    # Get residual values only where there are no edges
    noise_values = residual[non_edge_mask]
    
    if noise_values.size == 0:
        # Image is all edges (shouldn't happen, but handle it)
        return {
            "laplacian_variance": float(laplacian_variance),
            "residual_std": 0.0,
            "noise_score": 0.0,
        }
    
    # Robust noise metric: Median Absolute Deviation
    # More robust to outliers than standard deviation
    mad = np.median(np.abs(noise_values - np.median(noise_values)))
    residual_std = noise_values.std()
    
    return {
        "laplacian_variance": float(laplacian_variance),
        "residual_std": float(residual_std),
        "noise_score": float(mad),  # MAD is the real metric now!
    }


def classify_noise_level(noise_score: float) -> str:
    """
    Classify noise level based on MAD in non-edge areas.
    
    For line art:
    - Near 0-2: Clean vector-like art or high-quality scan
    - 3-8: Mild raster noise or JPEG compression artifacts
    - 10+: Visible fuzz, grain, or AI-generated speckle
    
    Args:
        noise_score: MAD metric from compute_noise_metrics
        
    Returns:
        One of: "low", "moderate", "high"
    """
    if noise_score < 3:
        return "low"
    elif noise_score < 10:
        return "moderate"
    else:
        return "high"


# ============================================================================
# Background Analysis
# ============================================================================

def analyze_background(image_path: Path) -> Tuple[str, float]:
    """
    Determine if image has a light or dark background.
    
    Uses mean brightness of the entire image. This helps us decide which
    direction to bias the blacklevel (threshold) parameter:
    - Light background (white + black lines) → test lower thresholds
    - Dark background (dark + light lines) → test higher thresholds
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (background_type, mean_brightness)
        where background_type is "light" or "dark"
        and mean_brightness is 0.0-1.0
    """
    # Load as grayscale
    img = Image.open(image_path).convert('L')
    img_array = np.array(img)
    
    # Calculate mean brightness (0-255 range)
    mean_brightness_raw = img_array.mean()
    
    # Normalize to 0.0-1.0
    mean_brightness = mean_brightness_raw / 255.0
    
    # Classify
    if mean_brightness >= config.BACKGROUND_BRIGHTNESS_THRESHOLD:
        bg_type = "light"
    else:
        bg_type = "dark"
    
    log_debug(f"Background analysis: {bg_type} (brightness={mean_brightness:.3f})")
    
    return bg_type, mean_brightness


# ============================================================================
# Combined Image Analysis
# ============================================================================

def analyze_image(image_path: Path) -> Dict:
    """
    Perform full analysis on an image: noise level and background type.
    
    This is the main entry point for image analysis - call this once
    per image to get all the info needed for parameter selection.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dict with keys:
            - noise_score: Combined noise metric
            - noise_level: "low", "moderate", or "high"
            - background_type: "light" or "dark"
            - mean_brightness: 0.0-1.0
            - width: Image width in pixels
            - height: Image height in pixels
    """
    log_info("Analyzing image characteristics...", style="cyan")
    
    # Load image for noise analysis (cv2 wants BGR/grayscale)
    img_cv = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img_cv is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Get dimensions
    height, width = img_cv.shape
    
    # Compute noise metrics
    noise_metrics = compute_noise_metrics(img_cv)
    noise_level = classify_noise_level(noise_metrics['noise_score'])
    
    # Analyze background
    bg_type, mean_brightness = analyze_background(image_path)
    
    # Log findings
    log_info(f"  Dimensions: {width}x{height} pixels")
    log_info(f"  Noise level: {noise_level.upper()} (score={noise_metrics['noise_score']:.1f})")
    log_info(f"  Background: {bg_type.upper()} (brightness={mean_brightness:.2f})")
    
    return {
        'noise_score': noise_metrics['noise_score'],
        'noise_level': noise_level,
        'background_type': bg_type,
        'mean_brightness': mean_brightness,
        'width': width,
        'height': height,
    }