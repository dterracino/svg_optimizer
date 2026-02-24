"""
Image Upscalers Package - AI-powered image enhancement for better tracing.

This package provides multiple upscaling backends:
- Real-ESRGAN: General purpose, optimized for line art (anime model)
- waifu2x: Specialized for line art with noise reduction
- Lanczos: Simple PIL-based fallback

Usage:
    from svg_optimizer.upscalers import create_upscaler, upscale_for_tracing
    
    upscaler = create_upscaler('realesrgan', scale=2)
    upscaler.initialize()
    upscaler.upscale_image(input_path, output_path)
    
    # Or use convenience function:
    result = upscale_for_tracing(input_path, method='auto', scale=2)
"""
import tempfile
from pathlib import Path
from typing import Optional, Literal

from .base import BaseUpscaler, detect_device, log_device_info
from .realesrgan import RealESRGANUpscaler
from .waifu2x import Waifu2xUpscaler
from .lanczos import LanczosUpscaler

from .. import log_info, log_success, log_warning, log_error, log_section, log_debug


# Export public API
__all__ = [
    'BaseUpscaler',
    'RealESRGANUpscaler',
    'Waifu2xUpscaler',
    'LanczosUpscaler',
    'create_upscaler',
    'upscale_for_tracing',
    'detect_device',
    'log_device_info',
]


def create_upscaler(
    method: Literal['realesrgan', 'waifu2x', 'lanczos', 'auto'] = 'auto',
    scale: int = 2,
    denoise_level: Optional[int] = None,
    device: Optional[str] = None
) -> BaseUpscaler:
    """
    Factory function to create an upscaler instance.
    
    Args:
        method: Upscaling method ('realesrgan', 'waifu2x', 'lanczos', 'auto')
        scale: Upscaling factor (2 or 4)
        denoise_level: Noise reduction level for waifu2x (0-3, default: 0=none)
        device: Force device ('cuda' or 'cpu'), None for auto-detect
        
    Returns:
        An initialized BaseUpscaler instance
        
    Auto Selection Logic:
        1. Try Real-ESRGAN first (best quality for line art)
        2. Fall back to waifu2x if Real-ESRGAN fails
        3. Fall back to Lanczos if both AI methods fail
    """
    if denoise_level is None:
        denoise_level = 0  # Default: no denoising unless explicitly requested
    
    # Handle auto selection
    if method == 'auto':
        # Try Real-ESRGAN first (best for line art with anime model)
        try:
            upscaler = RealESRGANUpscaler(scale=scale, device=device)
            if upscaler.initialize():
                return upscaler
            log_warning("Real-ESRGAN initialization failed, trying waifu2x...")
        except Exception as e:
            log_debug(f"Real-ESRGAN not available: {e}")
        
        # Try waifu2x as fallback
        try:
            upscaler = Waifu2xUpscaler(scale=scale, device=device, denoise_level=denoise_level)
            if upscaler.initialize():
                return upscaler
            log_warning("waifu2x initialization failed, using Lanczos fallback...")
        except Exception as e:
            log_debug(f"waifu2x not available: {e}")
        
        # Ultimate fallback to Lanczos
        upscaler = LanczosUpscaler(scale=scale, device=device)
        upscaler.initialize()
        return upscaler
    
    # Explicit method selection
    elif method == 'realesrgan':
        upscaler = RealESRGANUpscaler(scale=scale, device=device)
        if not upscaler.initialize():
            log_error("Failed to initialize Real-ESRGAN")
            raise RuntimeError("Real-ESRGAN initialization failed")
        return upscaler
    
    elif method == 'waifu2x':
        upscaler = Waifu2xUpscaler(scale=scale, device=device, denoise_level=denoise_level)
        if not upscaler.initialize():
            log_error("Failed to initialize waifu2x")
            raise RuntimeError("waifu2x initialization failed")
        return upscaler
    
    elif method == 'lanczos':
        upscaler = LanczosUpscaler(scale=scale, device=device)
        upscaler.initialize()
        return upscaler
    
    else:
        log_error(f"Unknown upscaler method: {method}")
        raise ValueError(f"Unknown upscaler method: {method}")


def upscale_for_tracing(
    image_path: Path,
    method: Literal['realesrgan', 'waifu2x', 'lanczos', 'auto'] = 'auto',
    scale: int = 2,
    denoise_level: Optional[int] = None,
    output_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Convenience function to upscale an image for SVG tracing.
    
    This function handles the complete upscaling workflow:
    - Device detection and logging
    - Upscaler creation and initialization
    - Image upscaling
    - Temporary file management
    
    Args:
        image_path: Input image path
        method: Upscaling method ('realesrgan', 'waifu2x', 'lanczos', 'auto')
        scale: Upscaling factor (2 or 4)
        denoise_level: Noise reduction level for waifu2x (0-3, default: 0=none)
        output_path: Output path (if None, creates temp file)
        
    Returns:
        Path to upscaled image, or None if failed
    """
    log_section("AI Image Upscaling")
    
    # Log device info
    log_device_info()
    
    try:
        # Create upscaler
        upscaler = create_upscaler(
            method=method,
            scale=scale,
            denoise_level=denoise_level
        )
        
        log_success(f"Upscaler ready: {upscaler.get_name()}")
        
        # Create output path if not provided
        if output_path is None:
            fd, temp_path = tempfile.mkstemp(suffix='.png', prefix='upscaled_')
            import os
            os.close(fd)
            output_path = Path(temp_path)
        
        # Perform upscaling
        success = upscaler.upscale_image(image_path, output_path)
        
        if success:
            log_success("Image upscaling successful!")
            return output_path
        else:
            log_error("Image upscaling failed")
            return None
            
    except Exception as e:
        log_error(f"Failed to upscale image: {e}")
        import traceback
        log_debug(traceback.format_exc())
        return None
