"""
Visual Logger Module - Create comparison sheets for optimization results.

This module generates a visual "proof sheet" showing all the parameter combinations
that were tested during optimization, arranged in a grid with scores and parameters
labeled. This lets you visually verify the optimizer picked the right one!

Think of it like a contact sheet in photography - you can see all the attempts at once.
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont
import numpy as np

from . import log_info, log_debug, log_error, log_success
from . import config
from .inkscape_wrapper import InkscapeWrapper


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ComparisonEntry:
    """Single entry in the comparison sheet."""
    svg_content: str
    params: Dict[str, float]
    score: float
    is_winner: bool = False


# ============================================================================
# Visual Logger Class
# ============================================================================

class VisualLogger:
    """
    Creates visual comparison sheets showing optimization results.
    
    The comparison sheet is a grid of thumbnails, each showing:
    - The rasterized SVG
    - The SSIM score (big and readable!)
    - Key parameters (threshold, smooth)
    - Green border if it's the winner
    """
    
    def __init__(self, inkscape: InkscapeWrapper):
        """
        Initialize the visual logger.
        
        Args:
            inkscape: InkscapeWrapper for rasterizing SVGs
        """
        self.inkscape = inkscape
        self._temp_dir = None
        log_debug("VisualLogger initialized")
    
    def create_comparison_sheet(
        self,
        entries: List[ComparisonEntry],
        output_path: Path,
        original_image: Path,
        target_width: int
    ) -> bool:
        """
        Create a visual comparison sheet from optimization results.
        
        This is the main entry point! It takes all the SVGs we tested,
        rasterizes them to thumbnails, arranges them in a grid, and
        saves one big PNG.
        
        Args:
            entries: List of ComparisonEntry objects (SVGs + scores + params)
            output_path: Where to save the comparison PNG
            original_image: Original input image (goes in top-left)
            target_width: Width to rasterize thumbnails at
            
        Returns:
            True if successful, False otherwise
        """
        if not entries:
            log_error("No entries to create comparison sheet from")
            return False
        
        log_info(f"Creating comparison sheet with {len(entries)} entries...")
        
        try:
            # Create temp directory for rasterized thumbnails
            import tempfile
            self._temp_dir = Path(tempfile.mkdtemp(prefix=config.TEMP_DIR_PREFIX))
            log_debug(f"Using temp directory: {self._temp_dir}")
            
            # Calculate thumbnail dimensions (maintain aspect ratio)
            with Image.open(original_image) as img:
                orig_width, orig_height = img.size
            
            thumb_width = config.THUMBNAIL_SIZE
            thumb_height = int(thumb_width * orig_height / orig_width)  # Ensure int!
            
            log_debug(f"Thumbnail size: {thumb_width}x{thumb_height}")
            
            # Rasterize all entries
            thumbnails = []
            
            # First: Add the original image
            original_thumb = self._create_original_thumbnail(
                original_image, thumb_width, thumb_height
            )
            thumbnails.append(original_thumb)
            
            # Then: Add all the tested SVGs
            for i, entry in enumerate(entries):
                log_debug(f"Rasterizing entry {i+1}/{len(entries)}")
                thumb = self._create_svg_thumbnail(
                    entry, thumb_width, thumb_height, i
                )
                if thumb:
                    thumbnails.append(thumb)
            
            # Arrange thumbnails in a grid
            grid_image = self._create_grid(
                thumbnails,
                columns=config.GRID_COLUMNS,
                padding=config.GRID_PADDING
            )
            
            # Save the final comparison sheet
            output_path.parent.mkdir(parents=True, exist_ok=True)
            grid_image.save(output_path, 'PNG')
            
            log_success(f"Saved comparison sheet: {output_path}")
            
            return True
            
        except Exception as e:
            log_error(f"Failed to create comparison sheet: {e}")
            return False
            
        finally:
            # Cleanup temp directory
            self._cleanup_temp()
    
    def _create_original_thumbnail(
        self,
        original_path: Path,
        width: int,
        height: int
    ) -> Image.Image:
        """
        Create a labeled thumbnail of the original image.
        
        This goes in the top-left of the grid with "ORIGINAL" label.
        
        Args:
            original_path: Path to original image
            width: Target width
            height: Target height
            
        Returns:
            PIL Image with label
        """
        # Load and resize original
        img = Image.open(original_path).convert('RGB')
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Add label at the top
        draw = ImageDraw.Draw(img)
        
        # Try to use a decent font, fall back to default if needed
        try:
            font = ImageFont.truetype("arial.ttf", config.LABEL_FONT_SIZE)
        except:
            font = ImageFont.load_default()
        
        # Draw "ORIGINAL" label with background
        label = "ORIGINAL"
        # Use textbbox instead of deprecated textsize
        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])
        
        # Black background for label
        label_bg = Image.new('RGB', (width, text_height + 10), color='black')
        img.paste(label_bg, (0, 0))
        
        # White text centered
        x = (width - text_width) // 2
        draw.text((x, 5), label, fill='white', font=font)
        
        return img
    
    def _create_svg_thumbnail(
        self,
        entry: ComparisonEntry,
        width: int,
        height: int,
        index: int
    ) -> Optional[Image.Image]:
        """
        Create a labeled thumbnail from an SVG entry.
        
        Shows the rasterized SVG with score and parameters overlaid.
        
        Args:
            entry: ComparisonEntry with SVG content and metadata
            width: Target width
            height: Target height
            index: Entry index (for temp file naming)
            
        Returns:
            PIL Image with labels, or None if rasterization failed
        """
        # Ensure temp dir exists
        if self._temp_dir is None:
            log_error("Temp directory not initialized")
            return None
        
        # Rasterize the SVG to a temp PNG
        temp_png = self._temp_dir / f"thumb_{index}.png"
        
        if not self.inkscape.rasterize_from_string(
            entry.svg_content,
            temp_png,
            width=width,
            height=height,
            temp_dir=self._temp_dir
        ):
            log_error(f"Failed to rasterize entry {index}")
            return None
        
        # Load the rasterized image
        img = Image.open(temp_png).convert('RGB')
        
        # Add border if this is the winner!
        if entry.is_winner:
            bordered = Image.new(
                'RGB',
                (width + 2*config.WINNER_BORDER_WIDTH, height + 2*config.WINNER_BORDER_WIDTH),
                color=config.WINNER_BORDER_COLOR
            )
            bordered.paste(img, (config.WINNER_BORDER_WIDTH, config.WINNER_BORDER_WIDTH))
            img = bordered
            width = img.width
            height = img.height
        
        # Create label with score and parameters
        draw = ImageDraw.Draw(img)
        
        try:
            font_score = ImageFont.truetype("arial.ttf", config.LABEL_FONT_SIZE + 4)
            font_params = ImageFont.truetype("arial.ttf", config.LABEL_FONT_SIZE - 2)
        except:
            font_score = ImageFont.load_default()
            font_params = ImageFont.load_default()
        
        # Format labels
        score_text = f"SSIM: {entry.score:.4f}"
        threshold_text = f"T: {entry.params.get('blacklevel', 0):.3f}"
        smooth_text = f"S: {entry.params.get('alphamax', 0):.2f}"
        
        # Draw score at the top (white text on black background)
        bbox = draw.textbbox((0, 0), score_text, font=font_score)
        score_height = int(bbox[3] - bbox[1])  # Ensure int
        score_bg = Image.new('RGB', (width, score_height + 10), color='black')
        img.paste(score_bg, (0, 0))
        
        draw.text((5, 5), score_text, fill='yellow' if entry.is_winner else 'white', font=font_score)
        
        # Draw parameters at the bottom
        param_text = f"{threshold_text}  {smooth_text}"
        bbox = draw.textbbox((0, 0), param_text, font=font_params)
        param_height = int(bbox[3] - bbox[1])  # Ensure int
        param_bg = Image.new('RGB', (width, param_height + 6), color='black')
        img.paste(param_bg, (0, height - param_height - 6))
        
        draw.text((5, height - param_height - 3), param_text, fill='cyan', font=font_params)
        
        return img
    
    def _create_grid(
        self,
        images: List[Image.Image],
        columns: int,
        padding: int
    ) -> Image.Image:
        """
        Arrange images in a grid layout.
        
        This does the actual grid math - figuring out how many rows we need,
        where each thumbnail goes, etc.
        
        Args:
            images: List of PIL Images (all should be same size!)
            columns: Number of columns in the grid
            padding: Pixels of padding between images
            
        Returns:
            Single PIL Image containing the grid
        """
        if not images:
            raise ValueError("No images to arrange in grid")
        
        # Calculate grid dimensions
        n_images = len(images)
        rows = (n_images + columns - 1) // columns  # Ceiling division
        
        # Get max thumbnail size (they might vary slightly due to borders)
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        
        # Calculate total grid size
        grid_width = columns * max_width + (columns - 1) * padding
        grid_height = rows * max_height + (rows - 1) * padding
        
        log_debug(f"Creating {rows}x{columns} grid ({grid_width}x{grid_height})")
        
        # Create blank canvas
        grid = Image.new('RGB', (grid_width, grid_height), color='white')
        
        # Paste images into grid
        for i, img in enumerate(images):
            row = i // columns
            col = i % columns
            
            x = col * (max_width + padding)
            y = row * (max_height + padding)
            
            grid.paste(img, (x, y))
        
        return grid
    
    def _cleanup_temp(self):
        """Clean up temporary directory and files."""
        if self._temp_dir and self._temp_dir.exists():
            import shutil
            shutil.rmtree(self._temp_dir)
            log_debug(f"Cleaned up temp directory: {self._temp_dir}")
            self._temp_dir = None
