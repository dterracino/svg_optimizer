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
        Check if waifu2x-ncnn-vulkan executable is available.

        Looks for waifu2x-ncnn-vulkan.exe in:
        1. PATH environment variable
        2. ./tools/waifu2x-ncnn-vulkan/ directory
        3. Current directory

        Returns:
            True if waifu2x executable is found, False otherwise
        """
        try:
            log_info(f"Checking for {self.get_name()}...")

            # Possible executable names
            exe_names = ['waifu2x-ncnn-vulkan.exe', 'waifu2x-ncnn-vulkan']

            # Check PATH first
            import shutil
            for exe_name in exe_names:
                exe_path = shutil.which(exe_name)
                if exe_path:
                    self.available = True
                    self.exe_path = exe_path
                    log_success(f"{self.get_name()} found in PATH: {exe_path}")
                    return True

            # Check common local directories
            from pathlib import Path
            search_dirs = [
                Path('./tools/waifu2x-ncnn-vulkan'),
                Path('./waifu2x-ncnn-vulkan'),
                Path('.'),
            ]

            for search_dir in search_dirs:
                for exe_name in exe_names:
                    exe_path = search_dir / exe_name
                    if exe_path.exists():
                        self.available = True
                        self.exe_path = str(exe_path.absolute())
                        log_success(f"{self.get_name()} found: {self.exe_path}")
                        return True

            log_warning("waifu2x-ncnn-vulkan not found")
            log_info("Download from: https://github.com/nihui/waifu2x-ncnn-vulkan/releases")
            log_info("Extract and either:")
            log_info("  1. Add to PATH, or")
            log_info("  2. Place in ./tools/waifu2x-ncnn-vulkan/ directory")
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
                # Run waifu2x-ncnn-vulkan executable
                # -i input, -o output, -n noise (denoise level), -s scale
                cmd = [
                    self.exe_path,
                    '-i', str(temp_input_path),
                    '-o', str(output_path),
                    '-n', str(self.denoise_level),
                    '-s', str(self.scale),
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
