"""
Lanczos Upscaler - Simple PIL-based fallback upscaler.

This is a lightweight fallback when AI upscalers aren't available.
Uses PIL's high-quality Lanczos resampling algorithm.
"""
from pathlib import Path
from typing import Optional
from PIL import Image

from .base import BaseUpscaler
from .. import log_info, log_success, log_warning, log_error, log_debug


class LanczosUpscaler(BaseUpscaler):
    """
    Simple Lanczos upscaler using PIL.
    
    This is a fallback upscaler that doesn't require PyTorch or other
    heavy dependencies. While not as sophisticated as AI upscalers,
    Lanczos resampling produces decent results for simple upscaling.
    
    Good for:
    - Systems without GPU
    - Quick testing
    - When AI models fail to load
    """
    
    def __init__(self, scale: int = 2, device: Optional[str] = None):
        """
        Initialize Lanczos upscaler.
        
        Args:
            scale: Output scale (2 or 4)
            device: Ignored (Lanczos doesn't use GPU)
        """
        super().__init__(scale, device)
    
    def get_name(self) -> str:
        """Return upscaler name for logging."""
        return f"Lanczos {self.scale}x (PIL fallback)"
    
    def initialize(self) -> bool:
        """
        Initialize Lanczos upscaler (always succeeds).
        
        Returns:
            Always True
        """
        log_warning(f"Using {self.get_name()} - AI upscalers not available")
        log_info("For better quality, install: pip install -r requirements-gpu.txt")
        return True
    
    def upscale_image(self, image_path: Path, output_path: Path) -> bool:
        """
        Upscale an image using Lanczos resampling.
        
        Args:
            image_path: Input image path
            output_path: Output image path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load image
            input_img = Image.open(image_path).convert('RGB')
            original_size = input_img.size
            log_info(f"Input image: {original_size[0]}x{original_size[1]} pixels")
            
            log_info(f"Upscaling with {self.get_name()}...")
            
            # Calculate new size
            new_size = (original_size[0] * self.scale, original_size[1] * self.scale)
            
            # Upscale using Lanczos resampling (high quality)
            output_img = input_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save
            output_img.save(output_path)
            
            log_success(f"Upscaling complete: {new_size[0]}x{new_size[1]} pixels")
            log_info(f"Output saved: {output_path}")
            
            return True
            
        except Exception as e:
            log_error(f"Lanczos upscaling failed: {e}")
            import traceback
            log_debug(traceback.format_exc())
            return False
