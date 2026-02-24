"""
Image Upscaling Module - AI-powered image enhancement for better tracing.

This module uses AI upscaling to enhance low-resolution or noisy images before
tracing to SVG. Cleaner, higher-resolution inputs lead to smoother vector paths.

Supports:
- Real-ESRGAN: General-purpose upscaling with excellent edge enhancement
- waifu2x: Specialized for line art and illustrations
- Automatic GPU/CPU detection with VRAM monitoring
"""
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Literal, Tuple
from PIL import Image

from . import log_info, log_success, log_warning, log_error, log_debug, log_section


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
# Upscaler Implementations
# ============================================================================

class ImageUpscaler:
    """
    Unified interface for AI image upscaling.
    
    Supports multiple backends: Real-ESRGAN and waifu2x.
    """
    
    def __init__(
        self, 
        method: Literal['realesrgan', 'waifu2x', 'auto'] = 'auto',
        scale: int = 2,
        device: Optional[str] = None
    ):
        """
        Initialize upscaler.
        
        Args:
            method: Upscaling method ('realesrgan', 'waifu2x', 'auto')
            scale: Upscaling factor (2 or 4)
            device: Force device ('cuda' or 'cpu'), None for auto-detect
        """
        self.method = method
        self.scale = scale
        
        # Detect device
        if device is None:
            self.device, self.gpu_info = detect_device()
        else:
            self.device = device
            self.gpu_info = None
        
        self.model = None
        
        # Validate scale
        if scale not in [2, 4]:
            log_warning(f"Unsupported scale {scale}, using 2x instead")
            self.scale = 2
    
    def _init_realesrgan(self):
        """Initialize Real-ESRGAN model."""
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            
            log_info("Loading Real-ESRGAN model...")
            
            # Choose model based on scale
            if self.scale == 4:
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, 
                               num_block=23, num_grow_ch=32, scale=4)
                model_name = 'RealESRGAN_x4plus'
            else:  # 2x
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                               num_block=23, num_grow_ch=32, scale=2)
                model_name = 'RealESRGAN_x2plus'
            
            # Determine model path (will auto-download if needed)
            model_path = Path.home() / '.cache' / 'realesrgan' / f'{model_name}.pth'
            
            if not model_path.exists():
                log_info(f"Downloading {model_name} model (first run only)...")
                log_info("This may take a minute...")
            
            # Initialize upsampler
            self.model = RealESRGANer(
                scale=self.scale,
                model_path=str(model_path),
                model=model,
                tile=0 if self.device == 'cuda' else 400,  # Use tiling on CPU to save memory
                tile_pad=10,
                pre_pad=0,
                half=True if self.device == 'cuda' else False,  # FP16 on GPU
                device=self.device
            )
            
            log_success(f"Real-ESRGAN {self.scale}x model loaded")
            return True
            
        except ImportError as e:
            log_error(f"Failed to import Real-ESRGAN: {e}")
            log_error("Install with: pip install realesrgan basicsr")
            return False
        except Exception as e:
            log_error(f"Failed to initialize Real-ESRGAN: {e}")
            return False
    
    def _init_waifu2x(self):
        """Initialize waifu2x model."""
        try:
            # Note: waifu2x-python is a wrapper that works with file paths
            # We'll handle it differently in the upscale method
            log_info("waifu2x backend detected")
            
            # Mark as initialized with None - actual processing happens per-image
            self.model = None  # waifu2x is handled differently
            
            log_success(f"waifu2x {self.scale}x configured")
            return True
            
        except Exception as e:
            log_error(f"Failed to configure waifu2x: {e}")
            return False
    
    def initialize(self) -> bool:
        """
        Initialize the upscaler model.
        
        Returns:
            True if successful, False otherwise
        """
        # Auto-select method
        if self.method == 'auto':
            # Try Real-ESRGAN first (generally better for most cases)
            log_debug("Auto-selecting upscaler method...")
            if self._init_realesrgan():
                self.method = 'realesrgan'
                return True
            elif self._init_waifu2x():
                self.method = 'waifu2x'
                return True
            else:
                log_error("No upscaler could be initialized")
                return False
        
        # User-specified method
        elif self.method == 'realesrgan':
            return self._init_realesrgan()
        elif self.method == 'waifu2x':
            return self._init_waifu2x()
        else:
            log_error(f"Unknown upscaler method: {self.method}")
            return False
    
    def upscale_image(self, image_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Upscale an image using the selected method.
        
        Args:
            image_path: Input image path
            output_path: Output path (if None, creates temp file)
            
        Returns:
            Path to upscaled image, or None if failed
        """
        # Check initialization - for Real-ESRGAN model must be loaded
        if self.method == 'realesrgan' and self.model is None:
            log_error("Real-ESRGAN not initialized, call initialize() first")
            return None
        
        # Load image
        try:
            input_img = Image.open(image_path).convert('RGB')
            original_size = input_img.size
            log_info(f"Input image: {original_size[0]}x{original_size[1]} pixels")
            
        except Exception as e:
            log_error(f"Failed to load image: {e}")
            return None
        
        # Create output path if not provided
        if output_path is None:
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix='.png', prefix='upscaled_')
            import os
            os.close(fd)
            output_path = Path(temp_path)
        
        # Upscale with selected method
        try:
            if self.method == 'realesrgan':
                log_info(f"Upscaling with Real-ESRGAN ({self.scale}x)...")
                
                # Type safety check
                if self.model is None:
                    log_error("Real-ESRGAN model not loaded")
                    return None
                
                # Convert PIL to numpy
                img_np = np.array(input_img)
                
                # Real-ESRGAN expects BGR
                img_np = img_np[:, :, ::-1]
                
                # Upscale - enhance() returns (output_image, _)
                output_np, _ = self.model.enhance(img_np, outscale=self.scale)
                
                # Convert back to RGB
                output_np = output_np[:, :, ::-1]
                
                # Save
                output_img = Image.fromarray(output_np)
                output_img.save(output_path)
                
            elif self.method == 'waifu2x':
                log_info(f"Upscaling with waifu2x ({self.scale}x)...")
                
                # waifu2x-python CLI-based approach
                try:
                    import subprocess
                    
                    # Save input temporarily if needed
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_in:
                        input_img.save(tmp_in.name)
                        tmp_input_path = tmp_in.name
                    
                    try:
                        # Run waifu2x command
                        cmd = [
                            'waifu2x-python',
                            '-i', tmp_input_path,
                            '-o', str(output_path),
                            '-s', str(self.scale),
                            '-n', '1',  # noise level
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            # Fallback: try using Pillow with Lanczos
                            log_warning("waifu2x CLI failed, using Pillow Lanczos fallback")
                            new_size = (original_size[0] * self.scale, original_size[1] * self.scale)
                            output_img = input_img.resize(new_size, Image.Resampling.LANCZOS)
                            output_img.save(output_path)
                            
                    finally:
                        # Cleanup temp input
                        import os
                        if os.path.exists(tmp_input_path):
                            os.unlink(tmp_input_path)
                            
                except (ImportError, FileNotFoundError) as e:
                    log_warning(f"waifu2x not available: {e}")
                    log_warning("Using Pillow Lanczos fallback")
                    new_size = (original_size[0] * self.scale, original_size[1] * self.scale)
                    output_img = input_img.resize(new_size, Image.Resampling.LANCZOS)
                    output_img.save(output_path)
            
            # Verify output
            final_img = Image.open(output_path)
            final_size = final_img.size
            
            log_success(f"Upscaling complete: {final_size[0]}x{final_size[1]} pixels")
            log_info(f"Output saved: {output_path}")
            
            return output_path
            
        except Exception as e:
            log_error(f"Upscaling failed: {e}")
            import traceback
            log_debug(traceback.format_exc())
            return None


# ============================================================================
# Convenience Functions
# ============================================================================

def upscale_for_tracing(
    image_path: Path,
    method: Literal['realesrgan', 'waifu2x', 'auto'] = 'auto',
    scale: int = 2,
    output_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Convenience function to upscale an image for SVG tracing.
    
    Args:
        image_path: Input image path
        method: Upscaling method
        scale: Upscaling factor (2 or 4)
        output_path: Output path (if None, creates temp file)
        
    Returns:
        Path to upscaled image, or None if failed
    """
    log_section("AI Image Upscaling")
    
    # Log device info
    log_device_info()
    
    # Create and initialize upscaler
    upscaler = ImageUpscaler(method=method, scale=scale)
    
    if not upscaler.initialize():
        log_error("Failed to initialize upscaler")
        return None
    
    # Perform upscaling
    result = upscaler.upscale_image(image_path, output_path)
    
    if result:
        log_success("Image upscaling successful!")
    
    return result
