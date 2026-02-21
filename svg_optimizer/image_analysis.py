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
    Compute noise-related metrics for a grayscale image.
    
    For line art (high contrast images), we primarily use residual analysis
    since Laplacian detects edges (which are good!) not noise (which is bad!).
    
    Args:
        image: Grayscale image as numpy array (uint8)
        
    Returns:
        Dict with keys:
            - laplacian_variance: High-frequency content level (for reference)
            - residual_std: Noise residual standard deviation  
            - noise_score: Residual std (Laplacian ignored for line art)
    """
    # Ensure float for precision
    img = image.astype(np.float32)
    
    # 1) Laplacian variance (high-frequency content)
    # For line art, this just detects edges, not noise!
    laplacian = cv2.Laplacian(img, cv2.CV_32F)
    laplacian_variance = laplacian.var()
    
    # 2) Noise residual (image - blurred image)
    # This is what actually matters for line art!
    # Clean edges → low residual
    # Fuzzy/noisy edges → high residual
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    residual = img - blurred
    residual_std = residual.std()
    
    # 3) For line art, use ONLY residual as noise score
    # Laplacian is useless here - it just detects edges!
    noise_score = residual_std
    
    return {
        "laplacian_variance": float(laplacian_variance),
        "residual_std": float(residual_std),
        "noise_score": float(noise_score),  # Just residual for line art!
    }


def classify_noise_level(noise_score: float) -> str:
    """
    Classify noise level based on residual std deviation.
    
    For line art, this measures how "fuzzy" the edges are.
    
    Args:
        noise_score: Residual std from compute_noise_metrics
        
    Returns:
        One of: "low", "moderate", "high"
    """
    # New thresholds based on residual_std only:
    # Clean line art: ~15-25
    # Moderate noise: ~25-40
    # High noise: 40+
    if noise_score < 25:
        return "low"
    elif noise_score < 40:
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
