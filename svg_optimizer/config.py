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
# Quality Level Presets
# ============================================================================
# These control how many parameter combinations to test
QUALITY_PRESETS = {
    'fast': {
        'blacklevel_samples': 3,  # Use every other value from range
        'alphamax_samples': 1,    # Just use default
        'estimated_time_min': 2,
    },
    'balanced': {
        'blacklevel_samples': 5,  # Use most of range
        'alphamax_samples': 3,    # Test all alphamax values
        'estimated_time_min': 5,
    },
    'thorough': {
        'blacklevel_samples': 6,  # Use entire range
        'alphamax_samples': 3,    # Test all alphamax values
        'estimated_time_min': 10,
    },
}

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
CLEANUP_TEMP_ON_SUCCESS = True
CLEANUP_TEMP_ON_ERROR = False  # Keep temps for debugging on failure