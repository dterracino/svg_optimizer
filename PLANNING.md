# SVG Auto-Optimizer - Project Planning Document

## Project Overview
A Python application that converts raster images (primarily line art and logos) to SVG format, automatically testing multiple parameter combinations to find the optimal conversion settings. Includes visual comparison logging to verify quality assessment.

## Core Objectives
1. Convert raster images to SVG using Inkscape CLI
2. Automatically optimize conversion parameters via grid search
3. Score outputs by comparing rasterized SVG against original (SSIM)
4. Generate visual comparison sheet of all tested combinations
5. Provide clear, real-time console feedback during processing

## Target Use Cases (v1)
- **Primary**: Black & white line art
- **Secondary**: Minimal palette line art (2-5 colors)
- **Purpose**: Generate clean SVGs for use in CAD tools like Fusion 360
- **Focus**: Outline quality over pixel-perfect reproduction

## Technical Architecture

### Module Structure
```
svg_optimizer/
├── __init__.py
├── __main__.py              # CLI entry point
├── inkscape_wrapper.py      # Inkscape CLI interface
├── image_comparer.py        # SVG quality assessment
├── parameter_grid.py        # Parameter combination generator
├── visual_logger.py         # Comparison sheet generator
├── config.py                # Constants and configuration
└── utils.py                 # Shared utilities
```

### Core Components

#### 1. PotraceTracer
**Responsibility**: Wrapper around `potracer` Python library for bitmap tracing

**Key Methods**:
- `trace_bitmap(input_path, output_path, params)` - Trace bitmap to SVG using potracer
- `load_and_prepare_bitmap(image_path, params)` - Load image, apply threshold/invert

**Why potracer (pure Python) instead of C potrace or pypotrace?**
- Inkscape's Trace Bitmap extension is not exposed via CLI (by design)
- pypotrace requires complex Windows compilation (MinGW, manual library builds)
- C potrace CLI requires binary distribution and subprocess management
- **potracer is pure Python** - installs via pip, no compilation needed!
- Clean Python API instead of command-line string building
- Same algorithm as original Potrace (port of v1.16)
- Performance: ~500x slower than C (but still fast enough for our offline use case)
- Optional numba JIT for 2x speedup if needed

**Potrace Parameters** (maps to Inkscape GUI):
- `blacklevel`: Threshold 0.0-1.0 (default 0.5) → **Inkscape's "Threshold"**
- `turdsize`: Suppress speckles, integer pixels (default 2) → **Inkscape's "Speckles"**
- `alphamax`: Corner threshold 0.0-1.34 (default 1.0) → **Inkscape's "Smooth corners"**
- `opttolerance`: Curve optimization 0.0-5.0 (default 0.2) → **Inkscape's "Optimize"**
- `turnpolicy`: black|white|left|right|minority|majority|random (default minority)

**Usage Pattern**:
```python
from potracer import Bitmap
import PIL.Image

# Load image
img = PIL.Image.open('input.png').convert('L')
# Apply threshold to create bitmap
bm = Bitmap(img, blacklevel=0.45)
# Trace with parameters
plist = bm.trace(turdsize=2, alphamax=1.0, opttolerance=5.0)
# Convert to SVG and save
```

#### 2. InkscapeWrapper
**Responsibility**: Manage Inkscape CLI for SVG rasterization only

**Key Methods**:
- `rasterize_svg(svg_path, output_path, width, height, dpi)` - Convert SVG to PNG
- `validate_installation()` - Check Inkscape is available
- `get_version()` - Get Inkscape version info

**Inkscape Path**: `C:\Program Files\Inkscape\bin\inkscape.exe`

#### 3. ImageComparer
**Responsibility**: Score SVG quality against original image

**Key Methods**:
- `compare(original_path, svg_path)` - Returns similarity score (0.0-1.0)
- `rasterize_for_comparison(svg_path, target_size)` - Prepare SVG for scoring using InkscapeWrapper
- `calculate_ssim(img1, img2)` - Structural similarity computation

**Scoring Strategy**:
- Use SSIM (Structural Similarity Index) as primary metric
- Rasterize SVG at original image dimensions using Inkscape
- Convert both to grayscale for B&W art comparison
- Score range: 0.0 (completely different) to 1.0 (identical)
- Downsample large images (>2000px) for faster comparison

**Dependencies**:
- `scikit-image` for SSIM calculation
- `Pillow` for image loading/manipulation
- `cv2` (OpenCV) for noise analysis
- InkscapeWrapper for SVG rasterization

#### 4. ParameterGrid
**Responsibility**: Generate optimal parameters using sequential binary search

**Key Insight:** We don't need to search a 3D parameter space! Each parameter affects different aspects:
- **Turdsize** → Noise removal (set once based on image analysis, not searched)
- **Threshold** → Gross shape boundaries (binary search FIRST - coarse adjustment)
- **Alphamax** → Curve smoothness (binary search SECOND - fine adjustment)  
- **Opttolerance** → Path joining (fixed at max, not searched)

These are mostly **separable** - changing one doesn't require re-optimizing the others!

**Key Methods**:
- `determine_turdsize(noise_level)` - Set speckle removal based on image analysis
- `binary_search_threshold(initial, step, tolerance)` - Find optimal threshold value
- `binary_search_smooth(initial, step, tolerance, fixed_threshold)` - Fine-tune smoothness
- `optimize_parameters(image_analysis)` - Main orchestrator

**Sequential Optimization Workflow:**

```python
# Step 1: Set turdsize (not optimized, just chosen)
if noise_level == "low":
    turdsize = 2       # Minimal - avoid eating letter holes
elif noise_level == "moderate":
    turdsize = 10      # Moderate removal
else:  # high
    turdsize = 50      # Aggressive despeckling

# Step 2: Binary search for threshold (8-10 iterations)
# This is the COARSE adjustment - gets the shapes right
best_threshold = binary_search(
    initial=0.45 if bg_type == "light" else 0.70,
    step=0.20,
    min_improvement=0.001,  # Stop when gains are tiny
)

# Step 3: Binary search for smooth (6-8 iterations)  
# This is the FINE adjustment - tweaks the details
best_smooth = binary_search(
    initial=1.0,
    step=0.3,
    min_improvement=0.001,
)
```

**Binary Search Algorithm:**
```
1. Start at initial value, score it
2. Try both directions (value ± step)
3. If either improved → move that direction, repeat
4. If neither improved → we're at a local peak, halve step size
5. Continue until step size < tolerance OR improvement < threshold
6. Return best value found
```

**Why This is Smarter Than Grid Search:**
- **Adaptive precision** - automatically zooms in on optimal values
- **Fewer evaluations** - ~14-18 total vs 20-30 for grid
- **Better results** - can find values between grid points
- **Separable optimization** - each parameter optimized independently

**Total Cost:**
- Turdsize: 0 iterations (just set it)
- Threshold: ~8-10 iterations (binary search)
- Smooth: ~6-8 iterations (binary search)
- **Total: 14-18 SVG generations** (vs 20-30 for grid search)

**Parameter Ranges** (used as search bounds):

```python
# Threshold bounds (direction depends on background)
THRESHOLD_BOUNDS_LIGHT_BG = (0.10, 0.70)  # White bg, black lines
THRESHOLD_BOUNDS_DARK_BG = (0.30, 1.00)   # Dark bg, light lines

# Smooth bounds (always same)
SMOOTH_BOUNDS = (0.5, 1.34)  # Potrace max is 1.34

# Turdsize options (noise-dependent, not searched)
TURDSIZE_LOW_NOISE = 2
TURDSIZE_MODERATE_NOISE = 10  
TURDSIZE_HIGH_NOISE = 50

# Opttolerance - locked
OPTTOLERANCE_VALUE = 5.0
```

#### 5. VisualLogger
**Responsibility**: Create comparison sheet showing all tested versions

**Key Methods**:
- `create_comparison_sheet(results, output_path)` - Generate final PNG
- `render_thumbnail(image, score, params)` - Create labeled thumbnail
- `layout_grid(thumbnails, columns)` - Arrange images in grid

**Layout Design**:
- Grid arrangement (auto-calculate columns based on count)
- Original image in top-left with "ORIGINAL" label
- Candidates sorted by score (best to worst)
- Each thumbnail shows:
  - Rasterized SVG preview
  - SSIM score (large, readable)
  - Key parameters (threshold, despeckle, smooth)
- Best result highlighted with green border
- Thumbnail size: ~300-400px wide

**Output**: Single large PNG file with complete comparison

#### 6. CLI Interface (\_\_main\_\_.py)
**Responsibility**: User-facing command-line interface

**Arguments**:
```
Required:
  input              Path to input image

Optional:
  -o, --output       Output SVG path (default: {input}.svg)
  -c, --comparison   Comparison sheet path (default: {input}_comparison.png)
  -q, --quality      Quality level: fast|balanced|thorough (default: balanced)
  -t, --type         Art type: lineart|color (default: lineart)
  -v, --verbose      Verbose output
  --no-comparison    Skip comparison sheet generation
  --log-json         Output parameter log as JSON
```

**Console Output Requirements**:
- Clear indication of current stage
- Progress bar for grid search (with percentage and ETA)
- Real-time updates on best score found so far
- Final summary with best parameters and file locations
- Use `rich` library for beautiful formatting

### Configuration (config.py)

```python
# External tool paths
INKSCAPE_PATH = r"C:\Program Files\Inkscape\bin\inkscape.exe"

# Output file naming
DEFAULT_OUTPUT_SUFFIX = ".svg"
DEFAULT_COMPARISON_SUFFIX = "_comparison.png"

# Potrace parameter defaults (Inkscape GUI defaults)
POTRACE_DEFAULTS = {
    'blacklevel': 0.45,      # Threshold (was 0.450 in GUI)
    'turdsize': 2,           # Speckles
    'alphamax': 1.0,         # Smooth corners  
    'opttolerance': 5.0,     # Optimize (we max this out)
    'turnpolicy': 'minority',
}

# Image analysis thresholds
NOISE_THRESHOLD_LOW = 50
NOISE_THRESHOLD_HIGH = 150
BACKGROUND_BRIGHTNESS_THRESHOLD = 0.5  # Above = light bg, below = dark bg

# Comparison settings
MAX_COMPARISON_DIMENSION = 2000  # Downsample larger images for SSIM
SSIM_GOOD_ENOUGH_THRESHOLD = 0.95  # Skip optimization if default is this good

# Visual logger settings  
THUMBNAIL_SIZE = 400  # pixels
GRID_PADDING = 20
LABEL_FONT_SIZE = 14
```

## Workflow

### Main Execution Flow
1. **Parse CLI arguments**
2. **Validate inputs and dependencies**
   - Check input file exists
   - Validate Inkscape installation (for rasterization)
   - Check output paths are writable
3. **Analyze input image**
   - Load image with Pillow
   - Detect background type (light vs dark via mean brightness)
   - Calculate noise level using noise.py algorithm
   - Determine initial parameter hints
4. **Try defaults first (quick test)**
   - Set turdsize based on noise analysis
   - Load bitmap with default blacklevel (0.45) using potracer
   - Trace with default parameters
   - Convert path list to SVG string
   - Rasterize result and calculate SSIM (using binary comparison!)
   - If SSIM > threshold (e.g., 0.95), we're done! Skip optimization.
5. **Sequential parameter optimization** (if defaults not good enough)
   - **Phase 1: Coarse adjustment (threshold)**
     - Binary search for optimal blacklevel value
     - Start from image-appropriate initial value (0.45 for light bg, 0.70 for dark)
     - Each iteration: test value, try both directions, move toward better score
     - Stop when improvements become negligible (~8-10 iterations)
     - Lock in best threshold
   - **Phase 2: Fine adjustment (smooth)**
     - Binary search for optimal alphamax value
     - Keep threshold fixed at best value from Phase 1
     - Start from 1.0, search range 0.5-1.34
     - Refine curve smoothness (~6-8 iterations)
     - Lock in best smooth value
   - **Total: ~14-18 SVG generations** (adaptive, finds exact sweet spots)
6. **Generate outputs**
   - Save best SVG to final output path
   - Create visual comparison sheet (if not disabled)
   - Generate JSON log with final parameters (if requested)
7. **Display summary**
   - Best parameters found (threshold, smooth, turdsize)
   - Final SSIM score
   - Comparison vs defaults (if optimization ran)
   - How many iterations each phase took
   - Output file locations
   - Total runtime

### Error Handling
- Graceful failure if Inkscape not found
- Clear error messages for invalid inputs
- Cleanup temporary files on failure
- Option to continue if individual conversions fail

## Dependencies

### Required Python Packages
- Python 3.9+
- `potracer` - Pure Python Potrace implementation for bitmap tracing
- `Pillow` - Image manipulation and loading
- `scikit-image` - SSIM calculation
- `opencv-python` (cv2) - Noise analysis
- `rich` - Console UI and progress bars
- `numpy` - Array operations (via scikit-image and cv2)

### Optional Performance Boost
- `numba` - JIT compiler for ~2x speedup on potracer (if platform supports it)

### External Binaries
- **Inkscape** - SVG to PNG rasterization (already installed at `C:\Program Files\Inkscape\bin`)

### System Requirements
- Windows (initial target, cross-platform later)
- ~100MB free disk space for temp files during processing

## Development Phases

### Phase 1: Core Infrastructure & SSIM Testing
- [ ] Project structure and config
- [ ] PotraceWrapper with basic trace functionality
- [ ] InkscapeWrapper for SVG rasterization
- [ ] **CRITICAL**: Build SSIM testing module first
  - [ ] Manual conversion workflow (you convert images in Inkscape)
  - [ ] Simple script to calculate SSIM between original and SVG
  - [ ] Determine "good enough" threshold empirically
- [ ] Test with known-good parameters
- [ ] Integrate noise detection from noise.py

### Phase 2: Optimization Engine
- [ ] ImageComparer with SSIM scoring and image analysis
- [ ] ParameterGrid implementation with noise/background detection
- [ ] Grid search loop with progress display
- [ ] Default-first quick test workflow

### Phase 3: Visual Output
- [ ] VisualLogger thumbnail generation  
- [ ] Grid layout system
- [ ] Comparison sheet creation

### Phase 4: Polish
- [ ] Error handling and edge cases
- [ ] JSON logging
- [ ] CLI help text and examples
- [ ] README with installation instructions
- [ ] Performance optimization if needed

## Testing Strategy
- **Unit tests**: Individual components with mock data
- **Integration tests**: Full pipeline with sample images
- **Test images**: Prepare 3-5 representative samples
  - Simple B&W line art
  - Complex B&W line art (logo)
  - 2-color artwork
  - 4-color artwork

## Future Enhancements (Post-v1)
- Auto-detect art type from image analysis
- Additional scoring metrics (perceptual color difference)
- Bayesian optimization for faster search
- Batch processing mode
- GUI wrapper
- SVG post-processing (simplification, cleanup)
- Export parameter presets for reuse

## Decisions Made

1. **Rasterization Method**: Use Inkscape CLI for SVG→PNG conversion
   - Guarantees consistency between trace and comparison
   - Already required as dependency

2. **Large Image Handling**: Downsample for SSIM comparison only
   - Use consistent resampling method for both original and SVG
   - Match resampling type to input characteristics (e.g., nearest neighbor for pixel art)
   - Important: Output SVG still uses original dimensions (separate issue to address)

3. **Intermediate File Storage**: Only save the best SVG
   - Visual log preserves record of all attempts
   - Parameters are logged for recreation
   - Saves disk space during grid search

4. **Baseline Comparison**: Include Inkscape's default parameters in grid
   - Provides reference point to verify optimization helps
   - First candidate in comparison sheet

## Notes
- Focus on console output quality - users should always know what's happening
- Keep temp files organized (use tempfile module)
- Consider adding dry-run mode for testing parameter grids without actual conversion
- SVG file size might be a secondary metric to track (not optimize for, just report)

---

**Document Version**: 1.0  
**Last Updated**: 2025-02-20  
**Status**: Pre-development planning