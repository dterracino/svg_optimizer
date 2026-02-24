"""
Waifu2x Upscaler - AI upscaling specialized for line art with noise reduction.

Waifu2x is specifically designed for anime and line art, with configurable
noise reduction levels. Ideal for cleaning up noisy scanned artwork.
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image

from .base import BaseUpscaler
from .. import log_info, log_success, log_warning, log_error, log_debug


class Waifu2xUpscaler(BaseUpscaler):
    """
    Waifu2x upscaler with noise reduction support.
    
    Features:
    - Specialized for line art and anime/manga
    - Configurable noise reduction (0-3)
    - Can be auto-configured based on image noise analysis
    """
    
    def __init__(self, scale: int = 2, device: Optional[str] = None, denoise_level: int = 0):
        """
        Initialize waifu2x upscaler.
        
        Args:
            scale: Output scale (2 or 4)
            device: 'cuda' or 'cpu' (auto-detected if None)
            denoise_level: Noise reduction level (0=none, 1=light, 2=medium, 3=heavy, default: 0)
        """
        super().__init__(scale, device)
        self.denoise_level = max(0, min(3, denoise_level))  # Clamp to 0-3
        self.available = False
    
    def get_name(self) -> str:
        """Return upscaler name for logging."""
        denoise_names = {0: "no denoise", 1: "light denoise", 2: "medium denoise", 3: "heavy denoise"}
        return f"waifu2x {self.scale}x ({denoise_names.get(self.denoise_level, 'denoise')})"
    
    def initialize(self) -> bool:
        """
        Check if waifu2x is available.
        
        Returns:
            True if waifu2x CLI is available, False otherwise
        """
        try:
            log_info(f"Checking for {self.get_name()}...")
            
            # Try to run waifu2x to check if it's available
            result = subprocess.run(
                ['waifu2x-python', '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.available = True
                log_success(f"{self.get_name()} available")
                return True
            else:
                log_warning("waifu2x-python not responding correctly")
                return False
                
        except FileNotFoundError:
            log_warning("waifu2x-python not found in PATH")
            log_info("Install with: pip install waifu2x-python")
            return False
        except subprocess.TimeoutExpired:
            log_warning("waifu2x-python timed out")
            return False
        except Exception as e:
            log_error(f"Failed to check waifu2x availability: {e}")
            log_debug(f"Error details: {e}")
            return False
    
    def upscale_image(self, image_path: Path, output_path: Path) -> bool:
        """
        Upscale an image using waifu2x.
        
        Args:
            image_path: Input image path
            output_path: Output image path
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            log_error("waifu2x not available")
            return False
        
        try:
            # Load image to report dimensions
            input_img = Image.open(image_path).convert('RGB')
            original_size = input_img.size
            log_info(f"Input image: {original_size[0]}x{original_size[1]} pixels")
            
            log_info(f"Upscaling with {self.get_name()}...")
            
            # Create temp input file if needed (waifu2x works with file paths)
            use_temp_input = False
            temp_input_path = image_path
            
            # If input has special characters or is already a temp file, make a copy
            try:
                str(image_path).encode('ascii')
            except UnicodeEncodeError:
                use_temp_input = True
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    input_img.save(tmp.name)
                    temp_input_path = Path(tmp.name)
            
            try:
                # Run waifu2x-python CLI
                cmd = [
                    'waifu2x-python',
                    '-i', str(temp_input_path),
                    '-o', str(output_path),
                    '-s', str(self.scale),
                    '-n', str(self.denoise_level),
                ]
                
                log_debug(f"Running: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout for large images
                )
                
                if result.returncode != 0:
                    log_error(f"waifu2x failed with return code {result.returncode}")
                    log_debug(f"stdout: {result.stdout}")
                    log_debug(f"stderr: {result.stderr}")
                    return False
                
                # Verify output
                if not output_path.exists():
                    log_error("waifu2x did not create output file")
                    return False
                
                final_img = Image.open(output_path)
                final_size = final_img.size
                
                log_success(f"Upscaling complete: {final_size[0]}x{final_size[1]} pixels")
                log_info(f"Output saved: {output_path}")
                
                return True
                
            finally:
                # Cleanup temp input if we created one
                if use_temp_input and temp_input_path.exists():
                    temp_input_path.unlink()
            
        except subprocess.TimeoutExpired:
            log_error("waifu2x timed out (image too large or processing too slow)")
            return False
        except Exception as e:
            log_error(f"waifu2x upscaling failed: {e}")
            import traceback
            log_debug(traceback.format_exc())
            return False
