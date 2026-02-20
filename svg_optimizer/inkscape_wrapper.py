"""
Inkscape Wrapper Module - SVG rasterization for quality comparison.

This module manages all interaction with Inkscape CLI, specifically for
converting SVG files back to PNG at specific dimensions so we can run
SSIM comparisons.

Why Inkscape? Because it's what the user already has installed, and it
guarantees consistent rendering (same engine that created the SVG in the
first place, if they used Inkscape manually).
"""
import subprocess
from pathlib import Path
from typing import Optional

from . import log_debug, log_info, log_error, log_warning
from . import config
from .utils import validate_external_tool


# ============================================================================
# Inkscape Wrapper Class
# ============================================================================

class InkscapeWrapper:
    """
    Clean wrapper around Inkscape CLI for SVG→PNG conversion.
    
    Keeps all the subprocess messiness contained in one place!
    """
    
    def __init__(self, inkscape_path: Optional[Path] = None):
        """
        Initialize Inkscape wrapper.
        
        Args:
            inkscape_path: Path to inkscape.exe (if None, uses config default)
        """
        self.inkscape_path = Path(inkscape_path) if inkscape_path else Path(config.INKSCAPE_PATH)
        self._validated = False
    
    def validate(self) -> bool:
        """
        Check that Inkscape exists and is accessible.
        
        Returns:
            True if Inkscape is ready to use, False otherwise
        """
        if self._validated:
            return True  # Already checked
        
        self._validated = validate_external_tool(self.inkscape_path, "Inkscape")
        return self._validated
    
    def rasterize(
        self,
        svg_path: Path,
        output_png: Path,
        width: Optional[int] = None,
        height: Optional[int] = None,
        dpi: Optional[int] = None
    ) -> bool:
        """
        Convert SVG to PNG using Inkscape.
        
        You can specify size either by dimensions (width/height) OR by DPI.
        If you specify width/height, it uses those exact dimensions.
        If you specify DPI, Inkscape renders at that resolution.
        If you specify nothing, Inkscape uses the SVG's natural size.
        
        Args:
            svg_path: Input SVG file
            output_png: Where to save PNG
            width: Target width in pixels (optional)
            height: Target height in pixels (optional)
            dpi: Rendering DPI (optional, ignored if width/height provided)
            
        Returns:
            True if successful, False otherwise
        """
        # Validate Inkscape is available
        if not self.validate():
            return False
        
        # Build command
        cmd = [
            str(self.inkscape_path),
            str(svg_path),
            '--export-type=png',
            f'--export-filename={output_png}',
        ]
        
        # Add size parameters
        if width is not None and height is not None:
            # Explicit dimensions - this is what we use for SSIM comparison
            # to ensure output matches original image size
            cmd.append(f'--export-width={width}')
            cmd.append(f'--export-height={height}')
            log_debug(f"Rasterizing to {width}x{height} pixels")
        elif width is not None:
            # Just width, Inkscape maintains aspect ratio
            cmd.append(f'--export-width={width}')
            log_debug(f"Rasterizing to width={width} (aspect ratio preserved)")
        elif height is not None:
            # Just height, Inkscape maintains aspect ratio
            cmd.append(f'--export-height={height}')
            log_debug(f"Rasterizing to height={height} (aspect ratio preserved)")
        elif dpi is not None:
            # DPI-based rendering
            cmd.append(f'--export-dpi={dpi}')
            log_debug(f"Rasterizing at {dpi} DPI")
        else:
            # No size specified - use SVG's natural dimensions
            log_debug("Rasterizing at SVG's natural size")
        
        # Execute Inkscape
        try:
            log_debug(f"Running Inkscape: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Inkscape shouldn't take more than 30 seconds
            )
            
            # Check if output file was created
            if not output_png.exists():
                log_error(f"Inkscape ran but didn't create output file: {output_png}")
                return False
            
            log_debug(f"Successfully rasterized to {output_png}")
            return True
            
        except subprocess.TimeoutExpired:
            log_error("Inkscape timed out (took more than 30 seconds)")
            return False
            
        except subprocess.CalledProcessError as e:
            log_error(f"Inkscape failed with exit code {e.returncode}")
            if e.stderr:
                log_debug(f"Inkscape stderr: {e.stderr}")
            return False
            
        except Exception as e:
            log_error(f"Unexpected error running Inkscape: {e}")
            return False
    
    def rasterize_from_string(
        self,
        svg_content: str,
        output_png: Path,
        width: int,
        height: int,
        temp_dir: Optional[Path] = None
    ) -> bool:
        """
        Rasterize SVG content (string) without needing an SVG file.
        
        This is useful in the optimization loop where we're generating
        SVGs on the fly and want to compare them quickly.
        
        Workflow:
        1. Write SVG string to temp file
        2. Rasterize temp file
        3. Clean up temp file
        
        Args:
            svg_content: SVG as a string
            output_png: Where to save PNG
            width: Target width
            height: Target height
            temp_dir: Where to put temp SVG (uses system temp if None)
            
        Returns:
            True if successful, False otherwise
        """
        import tempfile
        
        # Create temp SVG file
        try:
            if temp_dir:
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_svg = temp_dir / f"temp_{id(svg_content)}.svg"
            else:
                # Use system temp directory
                fd, temp_path = tempfile.mkstemp(suffix='.svg', text=True)
                temp_svg = Path(temp_path)
                # Close the file descriptor - we'll write with normal file operations
                import os
                os.close(fd)
            
            # Write SVG content
            with open(temp_svg, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            # Rasterize
            success = self.rasterize(temp_svg, output_png, width=width, height=height)
            
            # Clean up temp file
            if temp_svg.exists():
                temp_svg.unlink()
            
            return success
            
        except Exception as e:
            log_error(f"Failed to rasterize from string: {e}")
            return False
