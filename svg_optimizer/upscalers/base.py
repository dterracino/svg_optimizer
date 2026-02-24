"""
Base Upscaler Module - Abstract base class and GPU detection utilities.

This module provides the base class for all image upscalers and shared
utilities like GPU detection and VRAM monitoring.
"""
import torch
from pathlib import Path
from typing import Optional, Tuple
from abc import ABC, abstractmethod

from .. import log_info, log_success, log_warning, log_error, log_debug


# ============================================================================
# GPU Detection and Info
# ============================================================================

def detect_device() -> Tuple[str, Optional[dict]]:
    """
    Detect available compute device (GPU/CPU) and gather info.
    
    Returns:
        Tuple of (device_string, gpu_info_dict)
        - device_string: 'cuda', 'cpu'
        - gpu_info_dict: None if CPU, or dict with 'name', 'vram_total_gb', 'vram_free_gb'
    """
    if torch.cuda.is_available():
        device = 'cuda'
        gpu_info = {
            'name': torch.cuda.get_device_name(0),
            'vram_total_gb': torch.cuda.get_device_properties(0).total_memory / (1024**3),
            'vram_free_gb': (torch.cuda.get_device_properties(0).total_memory - 
                           torch.cuda.memory_allocated(0)) / (1024**3),
            'cuda_version': torch.version.cuda,
        }
        return device, gpu_info
    else:
        return 'cpu', None


def log_device_info():
    """Log detected GPU/CPU information with VRAM details."""
    device, gpu_info = detect_device()
    
    if device == 'cuda' and gpu_info:
        log_success(f"GPU detected: {gpu_info['name']}")
        log_info(f"  CUDA version: {gpu_info['cuda_version']}")
        log_info(f"  VRAM total: {gpu_info['vram_total_gb']:.2f} GB")
        log_info(f"  VRAM available: {gpu_info['vram_free_gb']:.2f} GB")
        log_debug(f"PyTorch version: {torch.__version__}")
    else:
        log_info("No GPU detected, using CPU")
        log_warning("CPU upscaling will be slower than GPU")
        log_debug(f"PyTorch version: {torch.__version__}")


# ============================================================================
# Base Upscaler Class
# ============================================================================

class BaseUpscaler(ABC):
    """
    Abstract base class for image upscalers.
    
    All upscaler implementations should inherit from this class and
    implement the abstract methods.
    """
    
    def __init__(self, scale: int = 2, device: Optional[str] = None):
        """
        Initialize upscaler.
        
        Args:
            scale: Upscaling factor (2 or 4)
            device: Force device ('cuda' or 'cpu'), None for auto-detect
        """
        self.scale = scale
        
        # Detect device
        if device is None:
            self.device, self.gpu_info = detect_device()
        else:
            self.device = device
            self.gpu_info = None
        
        # Validate scale
        if scale not in [2, 4]:
            log_warning(f"Unsupported scale {scale}, using 2x instead")
            self.scale = 2
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the upscaler (load models, etc.).
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def upscale_image(self, image_path: Path, output_path: Path) -> bool:
        """
        Upscale an image from input_path to output_path.
        
        Args:
            image_path: Input image path
            output_path: Output image path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name/description of this upscaler for logging.
        
        Returns:
            Human-readable name of the upscaler
        """
        pass
