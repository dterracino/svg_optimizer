"""
Configuration constants for SVG Auto-Optimizer.

All magic numbers, paths, and settings live here - single source of truth!
"""
from pathlib import Path

# ============================================================================
# External Tool Paths
# ============================================================================
INKSCAPE_PATH = r"C:\Program Files\Inkscape\bin\inkscape.exe"

# ============================================================================
# Output File Naming
# ============================================================================
DEFAULT_OUTPUT_SUFFIX = ".svg"
DEFAULT_COMPARISON_SUFFIX = "_comparison.png"
DEFAULT_JSON_LOG_SUFFIX = "_params.json"

# ============================================================================
# Potrace Parameter Defaults (matches Inkscape GUI defaults)
# ============================================================================
POTRACE_DEFAULTS = {
    'blacklevel': 0.45,      # Threshold (0.0-1.0)
    'turdsize': 2,           # Speckle suppression (pixels)
    'alphamax': 1.0,         # Corner smoothness (0.0-1.34)
    'opttolerance': 5.0,     # Curve optimization (0.0-5.0) - we max this out
    'turnpolicy': 'minority', # Ambiguity resolution
}

# ============================================================================
# Image Analysis Thresholds
# ============================================================================
# Noise levels (from noise.py algorithm)
NOISE_THRESHOLD_LOW = 50      # Below this = clean image, minimal despeckle
NOISE_THRESHOLD_HIGH = 150    # Above this = noisy, aggressive despeckle

# Background detection
BACKGROUND_BRIGHTNESS_THRESHOLD = 0.5  # Above = light bg, below = dark bg

# ============================================================================
# SSIM Comparison Settings
# ============================================================================
MAX_COMPARISON_DIMENSION = 2000  # Downsample images larger than this for SSIM
SSIM_GOOD_ENOUGH_THRESHOLD = 0.95  # Skip optimization if defaults score this high

# ============================================================================
# Parameter Grid Ranges
# ============================================================================
# Blacklevel ranges (direction depends on background analysis)
BLACKLEVEL_LIGHT_BG = [0.10, 0.25, 0.35, 0.45, 0.55, 0.65]  # For white bg + black lines
BLACKLEVEL_DARK_BG = [0.35, 0.45, 0.55, 0.70, 0.85, 1.00]   # For dark bg + light lines

# Turdsize ranges (depends on noise level)
TURDSIZE_LOW_NOISE = [0, 1, 2]           # Minimal - avoid eating holes in letters
TURDSIZE_MODERATE_NOISE = [0, 2, 5, 10]  # Wider range
TURDSIZE_HIGH_NOISE = [2, 10, 50, 100]   # Aggressive removal

# Alphamax (smooth corners) - stay close to default
ALPHAMAX_RANGE = [0.8, 1.0, 1.2]

# Opttolerance - locked at max for now
OPTTOLERANCE_VALUE = 5.0

# ============================================================================
# Binary Search Optimization Settings
# ============================================================================
# Threshold (blacklevel) binary search
THRESHOLD_INITIAL_LIGHT_BG = 0.45  # Starting point for light backgrounds
THRESHOLD_INITIAL_DARK_BG = 0.70   # Starting point for dark backgrounds
THRESHOLD_STEP_INITIAL = 0.20      # Initial step size
THRESHOLD_MIN_STEP = 0.02          # Stop when steps get this small
THRESHOLD_MIN_IMPROVEMENT = 0.001  # Stop when SSIM gains are tiny

# Smooth (alphamax) binary search  
SMOOTH_INITIAL = 1.0               # Always start at default
SMOOTH_STEP_INITIAL = 0.3          # Initial step size
SMOOTH_MIN_STEP = 0.05             # Stop when steps get this small
SMOOTH_MIN_IMPROVEMENT = 0.001     # Stop when SSIM gains are tiny

# Search bounds
THRESHOLD_BOUNDS_LIGHT_BG = (0.10, 0.70)
THRESHOLD_BOUNDS_DARK_BG = (0.30, 1.00)
SMOOTH_BOUNDS = (0.5, 1.34)  # Potrace's max smooth value is 1.34

# ============================================================================
# Turdsize (Speckles) Settings - Noise-Based Selection
# ============================================================================
TURDSIZE_LOW_NOISE = 2       # Clean images - minimal despeckle
TURDSIZE_MODERATE_NOISE = 10  # Some noise - moderate despeckle
TURDSIZE_HIGH_NOISE = 50      # Noisy images - aggressive despeckle

# ============================================================================
# Visual Logger Settings (for comparison sheet generation)
# ============================================================================
THUMBNAIL_SIZE = 400      # Pixels wide for each thumbnail
GRID_PADDING = 20         # Pixels between thumbnails
GRID_COLUMNS = 4          # Number of columns in comparison grid
LABEL_FONT_SIZE = 14      # Font size for parameter labels
WINNER_BORDER_COLOR = (0, 255, 0)   # Green border for best result
WINNER_BORDER_WIDTH = 5

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_FILE_NAME = "svg_optimizer.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = "INFO"  # Can be DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================================================================
# Temporary File Management
# ============================================================================
TEMP_DIR_PREFIX = "svg_optimizer_"
CLEANUP_TEMP_ON_SUCCESS = False
CLEANUP_TEMP_ON_ERROR = False  # Keep temps for debugging on failure
