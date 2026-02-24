"""
Real-ESRGAN Upscaler - AI upscaling optimized for line art and illustrations.

Uses the RealESRGAN_x4plus_anime_6B model which is specifically trained for
anime, illustrations, and line art - perfect for SVG tracing applications.
"""
import numpy as np
from pathlib import Path
from typing import Optional
from PIL import Image

from .base import BaseUpscaler
from .. import log_info, log_success, log_error, log_debug


class RealESRGANUpscaler(BaseUpscaler):
    """
    Real-ESRGAN upscaler using the anime/line art optimized model.
    
    Model: RealESRGAN_x4plus_anime_6B
    - Optimized for illustrations, line art, and anime
    - Better edge preservation than general models
    - Smaller download size (~17MB)
    - Native 4x scaling, can output 2x via outscale parameter
    """
    
    def __init__(self, scale: int = 2, device: Optional[str] = None):
        """
        Initialize Real-ESRGAN upscaler.
        
        Args:
            scale: Output scale (2 or 4)
            device: 'cuda' or 'cpu' (auto-detected if None)
        """
        super().__init__(scale, device)
        self.model = None
    
    def get_name(self) -> str:
        """Return upscaler name for logging."""
        return f"Real-ESRGAN {self.scale}x (anime model - optimized for line art)"
    
    def initialize(self) -> bool:
        """
        Initialize Real-ESRGAN model.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            
            log_info(f"Loading {self.get_name()}...")
            
            # Always use the 4x anime model (scales down to 2x if needed via outscale)
            model = RRDBNet(
                num_in_ch=3, 
                num_out_ch=3, 
                num_feat=64,
                num_block=6,  # anime model has 6 blocks instead of 23
                num_grow_ch=32, 
                scale=4
            )
            
            model_name = 'RealESRGAN_x4plus_anime_6B'
            
            # Model will be auto-downloaded to cache on first use
            model_path = Path.home() / '.cache' / 'realesrgan' / f'{model_name}.pth'
            
            if not model_path.exists():
                log_info(f"Downloading {model_name} model (~17MB, first run only)...")
                log_info("This may take a minute...")
            
            # Initialize upsampler
            self.model = RealESRGANer(
                scale=4,  # Model native scale (always 4x)
                model_path=str(model_path),
                model=model,
                tile=0 if self.device == 'cuda' else 400,  # Tiling on CPU saves memory
                tile_pad=10,
                pre_pad=0,
                half=True if self.device == 'cuda' else False,  # FP16 on GPU
                device=self.device
            )
            
            log_success(f"{self.get_name()} loaded successfully")
            return True
            
        except ImportError as e:
            log_error(f"Failed to import Real-ESRGAN: {e}")
            log_error("Install with: pip install realesrgan basicsr")
            return False
        except Exception as e:
            log_error(f"Failed to initialize Real-ESRGAN: {e}")
            import traceback
            log_debug(traceback.format_exc())
            return False
    
    def upscale_image(self, image_path: Path, output_path: Path) -> bool:
        """
        Upscale an image using Real-ESRGAN.
        
        Args:
            image_path: Input image path
            output_path: Output image path
            
        Returns:
            True if successful, False otherwise
        """
        if self.model is None:
            log_error("Real-ESRGAN model not initialized")
            return False
        
        try:
            # Load image
            input_img = Image.open(image_path).convert('RGB')
            original_size = input_img.size
            log_info(f"Input image: {original_size[0]}x{original_size[1]} pixels")
            
            log_info(f"Upscaling with Real-ESRGAN ({self.scale}x)...")
            
            # Convert PIL to numpy
            img_np = np.array(input_img)
            
            # Real-ESRGAN expects BGR format
            img_np = img_np[:, :, ::-1]
            
            # Upscale - the model always generates 4x internally,
            # but outscale parameter handles downsampling to 2x if needed
            output_np, _ = self.model.enhance(img_np, outscale=self.scale)
            
            # Convert back to RGB
            output_np = output_np[:, :, ::-1]
            
            # Save
            output_img = Image.fromarray(output_np)
            output_img.save(output_path)
            
            # Verify and report
            final_img = Image.open(output_path)
            final_size = final_img.size
            
            log_success(f"Upscaling complete: {final_size[0]}x{final_size[1]} pixels")
            log_info(f"Output saved: {output_path}")
            
            return True
            
        except Exception as e:
            log_error(f"Real-ESRGAN upscaling failed: {e}")
            import traceback
            log_debug(traceback.format_exc())
            return False
