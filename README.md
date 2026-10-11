# SVG Auto-Optimizer

[![PyPI version](https://badge.fury.io/py/svg-auto-optimizer.svg)](https://badge.fury.io/py/svg-auto-optimizer)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically optimize bitmap-to-SVG conversion parameters and add smooth vector outlines or rounded frames to existing SVG artwork.

**Version 0.2.0:** vector-only borders, Gaussian outline smoothing, rounded frames, physical and percentage units, automatic distance defaults, and progress reporting.
See [CHANGELOG.md](CHANGELOG.md) for release details and compatibility notes.

## Overview

SVG Auto-Optimizer takes the guesswork out of converting raster images (PNG, JPG, etc.) to vector SVGs. Instead of manually tweaking Potrace parameters in Inkscape until it "looks right," this tool automatically finds the optimal settings for your specific image.

**Key Features:**

- 🎯 **Smart optimization** - Sequential binary search instead of brute-force grid search
- 📊 **Quality scoring** - Binary SSIM comparison measures shape accuracy, not color
- 🚀 **Fast convergence** - Typically 14-18 evaluations vs 20-30+ for grid search
- 📸 **Visual proof sheets** - See all tested combinations in a comparison grid
- ⏭️ **Bail-early** - Skips optimization if defaults already score 0.95+
- **Vector borders** - Gaussian-smoothed silhouette outlines or rectangular frames with rounded corners, without rasterization
- **Convenient border distances** - Millimeters, inches, percentages, or SVG units, with scale-aware defaults
- **Safe border generation** - Minimum-clearance checks, early curve-budget errors, and visible generation progress

**Perfect for:**

- Converting logos and line art for CAD software (Fusion 360, etc.)
- Preparing vector graphics from scanned drawings
- Batch processing images with consistent quality

## Installation

### Prerequisites

- Python 3.11 (the project's target runtime)
- [Inkscape](https://inkscape.org/) installed and accessible from command line for bitmap tracing and comparison (not required for existing-SVG border mode)

This project is built for Python 3.11. Use Python 3.11 when creating your virtual environment: the pinned PyTorch 2.1.2 and torchvision 0.16.2 dependencies in the CPU/GPU requirements do not provide Windows wheels for Python 3.12 or newer.

### Install from PyPI (Recommended)

**Basic installation (core features only):**

```bash
pip install svg-auto-optimizer
```

**With AI upscaling (CPU):**

```bash
pip install svg-auto-optimizer[cpu]
```

**With AI upscaling (GPU - NVIDIA CUDA):**

```bash
pip install svg-auto-optimizer[gpu]
```

After installation, the tool is available as `svg-optimizer`:

```bash
svg-optimizer --help
svg-optimizer myimage.png
```

### Install from Source

1. Clone the repository:

```bash
git clone https://github.com/yourusername/svg-auto-optimizer.git
cd svg-auto-optimizer
```

1. Create and activate a virtual environment:

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

1. Install dependencies:

**Choose your installation based on your hardware:**

```bash
# For GPU acceleration (NVIDIA GPU with CUDA support)
pip install -r requirements-gpu.txt

# For CPU-only (no GPU required)
pip install -r requirements-cpu.txt
```

The GPU version enables:

- **AI Upscaling** - Real-ESRGAN and waifu2x for image enhancement
- **Background Removal** - rembg for automatic background removal
- Faster processing on CUDA-capable GPUs

The CPU version includes the same features but runs on CPU only (slower but works everywhere).

**Core tracing features work with either installation.**

When switching an existing environment, uninstall `opencv-python` first (`pip uninstall opencv-python`) so only one OpenCV wheel provides the `cv2` module.

## Usage

### Basic Usage

```bash
# Simple - optimize and save as input.svg
python -m svg_optimizer logo.png

# Or use the wrapper script
python svg_optimize.py logo.png
```

### Common Options

```bash
# Specify custom output location
python -m svg_optimizer logo.png --output my_logo.svg

# AI upscale before tracing (improves quality for low-res/noisy images)
python -m svg_optimizer logo.png --upscale

# Upscale with specific method and factor
python -m svg_optimizer logo.png --upscale --upscale-method realesrgan --upscale-factor 4

# Skip optimization, just use defaults (fast!)
python -m svg_optimizer logo.png --skip-optimization

# Manual threshold override
python -m svg_optimizer logo.png --threshold 0.35

# Skip the comparison sheet
python -m svg_optimizer logo.png --no-comparison

# Verbose debug output
python -m svg_optimizer logo.png --verbose
```

### Vector-Only SVG Borders

Add a border to an existing SVG without rendering it to pixels or retracing the original artwork:

```powershell
# Automatically choose distances from the SVG's coordinate scale
python -m svg_optimizer samples\jack.svg --border

# Wide, smooth border using millimeters instead of large SVG coordinates
python -m svg_optimizer samples\jack.svg --border-units mm --border-offset 5 --border-smoothing 10 --border-width 0.2

# Percentages of the shorter canvas side: 2% offset, 5% smoothing
python -m svg_optimizer samples\jack.svg --border-units percent --border-offset 2 --border-smoothing 5

# Rectangular frame around visible artwork, with 3 mm rounded corners
python -m svg_optimizer samples\jack.svg --border-type frame --border-units mm --border-offset 5 --corner-radius 3 --border-width 0.2

# Large rounded corners: radius is independent of the minimum clearance
python -m svg_optimizer samples\jack.svg --border-type frame --border-units mm --border-offset 10 --corner-radius 15 --border-width 0.2

python -m svg_optimizer logo.svg --border-offset 5 --border-smoothing 10

# Specify border appearance and output
python -m svg_optimizer logo.svg --border-offset 5 --border-smoothing 10 --border-width 1 --border-color "#0066cc" --output logo_framed.svg

# Use a larger smoothing radius for high-coordinate-resolution artwork
python -m svg_optimizer samples\portal-eye.svg --border-offset 30 --border-smoothing 100 --border-tolerance 0.25

# Also add a vector border to the result of normal bitmap tracing
python -m svg_optimizer logo.png --border-offset 5 --border-smoothing 10
```

Border outputs default to `{filename}_border_{type}_{offset}{unit}.svg`, for both existing SVGs and traced raster inputs.
For example, the 5 mm frame command above saves `jack_border_frame_5mm.svg`; the 10 mm frame saves `jack_border_frame_10mm.svg`, and a 2% outline saves `jack_border_outline_2percent.svg`.
Automatic offsets are resolved before naming, using the selected unit.
An explicit `--output` overrides this naming; the source SVG cannot be overwritten.
SVG border mode does not load the raster tracing pipeline, invoke Inkscape, or generate a comparison sheet.
CLI border generation shows the current stage, an activity spinner, and elapsed time for that stage.
Sampling and fitted-curve validation show measured counts and stage percentages; artwork flattening reports processed source segments.
Curve fitting reports each attempt (up to six), so outward refitting is visible.
Offsetting, unioning, and buffer-based smoothing are indivisible geometry operations: they show activity rather than a fabricated percentage or ETA.
Gaussian perimeter averaging reports processed sample counts.
Stage changes are also logged, including when output writing starts; a saved message appears only after the write succeeds.
The spinner indicates an active progress display, not a guarantee that a geometry operation is making forward progress.
Library calls remain quiet by default; use `SVGBorderGenerator(..., show_progress=True)` to enable the same display.
Raster inputs retain the normal tracing workflow; the border is added only to the final SVG, after scoring and optimization.
Reported SSIM scores and comparison sheets describe the artwork **before** the border is added.

| Option | Default | Meaning |
| --- | --- | --- |
| `--border` | Disabled | Enable border generation with automatic distances for any omitted options. |
| `--border-type`, `--border-style` | `outline` | `outline` follows the smoothed outer silhouette; `frame` draws a bounding-box border. |
| `--corner-radius` | `0` | Frame centerline corner radius in the selected units. Zero makes square corners. Not valid for outline borders. |
| `--border-units` | `svg` | Units for all explicit distances: `svg`, `mm`, `cm`, `in`, `px`, `pt`, `pc`, or `percent`. |
| `--border-offset` | Automatic with `--border` | Enable the border and set its minimum clearance from the artwork to the border stroke's inner edge. Must be positive. |
| `--border-smoothing` | Automatic (outline only) | Gaussian standard deviation along the outline perimeter, also used for gap bridging and notch closing. Larger values suppress broader details; `0` skips Gaussian averaging and broad smoothing, but retains a tight cubic fit and connects separate pieces. Rejected for frames. |
| `--border-tolerance` | Automatic | Maximum vector curve-flattening error for artwork processing and clearance verification. Smaller values preserve more detail and require more processing. |
| `--border-width` | Automatic | Positive border stroke width. |
| `--border-color` | `black` | Visible color name or quoted `#RGB`/`#RRGGBB` value. |

**Distances default to root SVG user coordinates.** Use `--border-units` to specify physical distances or percentages instead.
For example, a `viewBox="0 0 100 100"` displayed at `width="50mm"` has a horizontal scale of 0.5 mm per user unit.

The chosen unit applies to every explicit offset, smoothing, tolerance, stroke-width, and corner-radius value.
With `--border-units percent`, the number `5` means 5% of the **shorter original viewBox/canvas side**, not 5% of the artwork bounds.
Use plain numbers with the flag, not suffixes such as `5mm` or `5%`.
Omitted distances retain their automatic defaults in SVG coordinates; they are not reinterpreted in the chosen unit.
Conversions happen before preflight and geometry processing, and progress displays the resolved SVG-unit distances.

Physical units follow the original root dimensions and `preserveAspectRatio` scaling, with 96 CSS pixels per inch.
They require absolute `width` and `height` when a viewBox is present; missing dimensions are rejected instead of assuming a physical size.
With no viewBox, root user coordinates already correspond to CSS pixels.
Non-uniform `preserveAspectRatio="none"` scaling is rejected for physical units because one circular offset cannot have the same physical size along both axes.
Use `svg` or `percent` in those cases. Pixel units are CSS pixels, not raster-image pixels, and external browser/CSS resizing can change the displayed physical size.
The source artwork coordinates are never rescaled.

CLI automatic distances use `s = min(viewBox width, viewBox height) / 210` (or the resolved viewport without a viewBox).
The defaults are offset `s`, smoothing `2*s`, tolerance `0.005*s`, and stroke width `0.1*s`.
For `jack.svg` this selects `100`, `200`, `0.5`, and `10`, respectively.
These are proportional starting values, not automatic physical-unit conversion or a guarantee that every SVG will fit.
Resolved values are displayed before geometry processing; explicit options, including zero smoothing, are never replaced.
Library numeric defaults remain unchanged; pass `None` for individual distances to request scale-aware resolution, and `units="mm"` or `units="percent"` to convert explicit distances.

For outline borders, a preflight checks a lower bound on the required cubic count using visible artwork endpoints before expensive curve flattening, offsetting, or smoothing.
Clearly excessive settings fail with the estimated minimum count, the 10,000-curve limit, and a suggested minimum smoothing value.
Passing preflight is not a guarantee: concavities, curves, and later outward corrections can require more segments, so the final budget and clearance checks remain in place.

**Frame borders** use the visible filled artwork's bounding box (including transforms and disconnected pieces), not the root canvas.
The box is expanded by the offset plus half the stroke width and a conservative curve-approximation margin.
Frames are SVG rectangles with native rounded corners; they skip outline bridging, smoothing, spline fitting, and the cubic-count budget.
`--border-smoothing` is rejected in frame mode; use `--corner-radius` instead.
Rounded corners are checked against the actual artwork, not imaginary filled corners of its bounding box.
Large radii are allowed when the empty corner regions provide enough room for the requested clearance.
There is no rule limiting the radius to the offset: the `jack.svg` example with a 10 mm offset and 15 mm radius fits without additional frame expansion.
If necessary, the frame expands equally on all four sides by the smallest safe amount found within the geometry tolerance, while keeping the requested radius unchanged.
This also ensures the frame dimensions can accommodate the radius without SVG's automatic radius clamping.
Progress reports clearance checking and the expansion search; any additional expansion is logged in the selected units.
The offset remains a minimum clearance, so expanded frames may have more space along straight sides.
The canvas expands to include the frame's full stroke. Artwork and supported-input restrictions remain unchanged.
Library callers can select `border_type="frame"` and `corner_radius=3`.

The default **outline** mode of [SVGBorderGenerator](svg_optimizer/svg_border.py) uses `svgelements` to resolve filled shapes and transforms and Shapely to construct vector geometry.
It connects disconnected pieces, smooths small recesses, and keeps all supported artwork enclosed with at least the requested clearance.
Broad recesses can remain; this is not a convex-hull or rectangular frame.
A distant speck must still influence the border because it cannot be left outside.
Larger smoothing values can bridge larger recesses and increase the distance beyond the requested minimum.

The original artwork's paths and shape attributes are retained.
The outline border is a closed **cubic Bezier path**, fitted from evenly spaced perimeter samples using a periodic cubic B-spline.
Its tangent and second derivative remain continuous at every join, including the closing seam, so curved artwork does not acquire polygon corners.
Coarse polygon simplification is not used; larger smoothing radii average small outline irregularities before the final curves are written.
Uniform perimeter samples are averaged with Gaussian weights `exp(-distance^2 / (2*smoothing^2))`, normalized to sum to one and truncated at four standard deviations.
The averaging wraps around the closed perimeter, including the closing seam, and suppresses both small outward bumps and inward notches before spline fitting.
Increasing smoothing widens this averaging neighborhood, simplifying small-scale details while retaining broader features where compatible with enclosure.
Strong smoothing can also soften large recesses; it does not guarantee a strictly simpler shape for every possible input because all artwork and minimum clearance must remain protected.
The existing vector closing step remains for gap and notch handling.
The original artwork remains unchanged, and border generation uses no rasterization or additional dependencies beyond the vector libraries above.
This remains an approximate vector offset, not an exact analytic Bezier offset.
Conservative margins compensate for approximation error.
The **fitted cubic curve**, not just its preliminary polygon, is checked for enclosure and minimum clearance using a finer vector approximation.
If fitting pulls the border inward, the enclosing outline is expanded and refitted while preserving smooth joins.
Unsafe fits fail explicitly rather than falling back to straight segments.
The SVG canvas expands to include the curves' control-point bounds and full stroke while preserving the artwork's coordinate scale.
XML formatting and namespace prefixes may change when the document is saved.

**Supported SVG inputs:** filled paths (including cubic/quadratic curves and arcs), rectangles, rounded rectangles, circles, ellipses, polygons, filled polylines, and group/shape transforms.
Holes do not receive inner borders.
Documents must be UTF-8 encoded and need a valid `viewBox` or absolute width and height; percentage dimensions are unsupported.
The root must use the SVG namespace. Root-level transforms are unsupported; place transformed artwork in a group instead.
Rendering hints (`shape-rendering`, `text-rendering`, `image-rendering`, and `clip-rule`) are accepted and preserved.
Embedded stylesheets may contain simple `.class { ... }` rules using supported presentation properties, including fills and opacity.
Rules are resolved in source order on a geometry-only copy, with inline styles taking precedence; the saved artwork keeps its original classes and stylesheets.
Complex selectors, conditional stylesheets, external CSS, `!important`, and unresolved classes are rejected explicitly.
Stroked artwork, text, embedded images, `<use>` references, nested SVGs, clipping, masks, filters, and paint servers are rejected explicitly.
Convert text and strokes to filled paths and flatten unsupported effects before using border mode.
Border styling options require `--border` or `--border-offset`; raster-only options cannot be combined with existing SVG input.
An SVG already containing the generated `svg-optimizer-border` element is rejected rather than given a second border; use the original artwork when changing border settings.

### AI Upscaling

For low-resolution or noisy images, AI upscaling can significantly improve tracing quality by enhancing edges before vectorization:

```bash
# Enable upscaling with auto-detection (tries Real-ESRGAN first)
python -m svg_optimizer lowres.png --upscale

# Use specific upscaler
python -m svg_optimizer lowres.png --upscale --upscale-method realesrgan  # Best for line art
python -m svg_optimizer lowres.png --upscale --upscale-method waifu2x     # With noise reduction

# 4x upscaling for very small images
python -m svg_optimizer tiny_logo.png --upscale --upscale-factor 4

# waifu2x with noise reduction (for noisy/scanned images)
python -m svg_optimizer noisy.png --upscale --upscale-method waifu2x --upscale-denoise 2
```

**Upscaler Details:**

- **Real-ESRGAN** (default) - Uses `RealESRGAN_x4plus_anime_6B` model optimized for line art and illustrations
  - ~17MB model size
  - Better edge preservation than general models
  - Best for clean line art
  
- **waifu2x** - Specialized for anime/line art with configurable noise reduction
  - `--upscale-denoise 0` = No denoising (default)
  - `--upscale-denoise 1` = Light denoising
  - `--upscale-denoise 2` = Medium denoising  
  - `--upscale-denoise 3` = Heavy denoising
  - Best for noisy scanned artwork

- **Lanczos** - Automatic fallback if AI methods unavailable
  - Simple PIL-based resampling
  - No PyTorch required

**Benefits:**

- 🎨 Smoother vector paths from cleaner edges
- 📏 Better detail preservation in small images
- 🔧 Reduces noise artifacts in the final SVG

**GPU Acceleration:**

- Automatically detects NVIDIA GPU and CUDA support
- Displays GPU name and VRAM information
- Falls back to CPU if GPU unavailable (slower)

### Full Options

```text
usage: python -m svg_optimizer [-h] [-o OUTPUT] [-c COMPARISON] [--no-comparison]
                               [--skip-optimization] [--threshold THRESHOLD]
                               [--upscale] [--upscale-method {realesrgan,waifu2x,auto}]
                               [--upscale-factor {2,4}]
                               [--border] [--border-offset BORDER_OFFSET]
                               [--border-units {svg,mm,cm,in,px,pt,pc,percent}]
                               [--border-smoothing BORDER_SMOOTHING]
                               [--border-tolerance BORDER_TOLERANCE]
                               [--border-width BORDER_WIDTH] [--border-color BORDER_COLOR]
                               [-v] [--log-file LOG_FILE]
                               input

positional arguments:
  input                 Input raster image, or existing SVG with --border or --border-offset

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output SVG file path (default: input_border_TYPE_SIZEUNIT.svg with border, input.svg otherwise)
  -c COMPARISON, --comparison COMPARISON
                        Comparison sheet PNG path (default: input_comparison.png)
  --no-comparison       Skip generating the visual comparison sheet
  --skip-optimization   Skip parameter optimization, just use defaults
  --threshold THRESHOLD
                        Override: Set specific threshold value (0.0-1.0)
  --upscale             Enable AI upscaling before tracing (improves edge quality)
  --upscale-method {realesrgan,waifu2x,lanczos,auto}
                        AI upscaling method (default: auto)
  --upscale-factor {2,4}
                        Upscaling factor: 2x or 4x (default: 2)
  --upscale-denoise {0,1,2,3}
                        Denoise level for waifu2x: 0=none, 1=light, 2=medium, 3=heavy (default: 0)
  -v, --verbose         Enable verbose debug output
  --log-file LOG_FILE   Custom log file path (default: svg_optimizer.log)

vector border (distances in --border-units):
  --border-type {outline,frame}, --border-style {outline,frame}
                        Border type (default: outline)
  --corner-radius CORNER_RADIUS
                        Frame centerline corner radius (default: 0)
  --border              Enable border with automatic distances
  --border-units {svg,mm,cm,in,px,pt,pc,percent}
                        Units for explicit distances (default: svg)
  --border-offset BORDER_OFFSET
                        Enable border with this minimum clearance
  --border-smoothing BORDER_SMOOTHING
                        Smoothing radius (default: automatic SVG scale; 0 keeps a tight cubic fit)
  --border-tolerance BORDER_TOLERANCE
                        Maximum vector curve-flattening error (default: automatic SVG scale)
  --border-width BORDER_WIDTH
                        Border stroke width (default: automatic SVG scale)
  --border-color BORDER_COLOR
                        Border stroke color (default: black)
```

## How It Works

### 1. AI Upscaling (Optional)

If enabled with `--upscale`, enhances the input image before tracing:

- **Real-ESRGAN** - Uses anime/line art optimized model (RealESRGAN_x4plus_anime_6B)
  - Better edge preservation for illustrations
  - Handles both 2x and 4x scaling
- **waifu2x** - Specialized for line art with configurable noise reduction (0-3)
  - Best for noisy scanned artwork
- **Lanczos** - Simple fallback when AI models unavailable
- Automatically detects and uses GPU if available
- Reports GPU name and VRAM information

### 2. Image Analysis

Analyzes your input image (original or upscaled) to determine:

- **Noise level** - How much speckle removal is needed
- **Background type** - Light vs dark (affects threshold search range)

### 3. Try Defaults First

Tests Inkscape's default parameters (threshold=0.45, smooth=1.0). If the SSIM score is ≥0.95, optimization is skipped entirely!

### 4. Sequential Binary Search Optimization

If defaults aren't good enough, runs two optimization phases:

#### Phase 1: Threshold (Coarse Adjustment)

- Determines WHERE shapes are detected
- Binary search finds optimal blacklevel value
- ~8-10 iterations to converge

#### Phase 2: Smooth (Fine Adjustment)

- Tweaks HOW curves are represented
- Binary search finds optimal alphamax value
- ~6-8 iterations to converge

**Total:** ~14-18 SVG generations (vs 20-30+ for grid search)

### 5. Generate Outputs

- **Optimized SVG** - Best result found
- **Comparison sheet** (optional) - Visual grid showing all tested combinations with scores

## Understanding SSIM Scores

SSIM (Structural Similarity Index) scores range from 0.0 to 1.0:

- **0.95+** - Excellent! Shapes match nearly perfectly
- **0.90-0.95** - Very good, minor differences
- **0.85-0.90** - Good, but noticeable differences
- **0.80-0.85** - OK, optimization recommended
- **<0.80** - Poor, significant differences

We use **binary SSIM** (threshold both images to pure B&W before comparing) because CAD tools only care about shape boundaries, not colors or gradients.

## Project Structure

```text
svg_optimizer/
├── svg_optimizer/          # Main package
│   ├── __init__.py         # Package initialization & logging exports
│   ├── __main__.py         # CLI application entry point
│   ├── config.py           # All configuration constants
│   ├── utils.py            # Unified logging & helper functions
│   ├── cli.py              # Command-line argument parsing
│   ├── image_analysis.py   # Noise & background detection
│   ├── upscalers/          # AI upscaling package
│   │   ├── __init__.py     # Upscaler factory & public API
│   │   ├── base.py         # Base class & GPU detection
│   │   ├── realesrgan.py   # Real-ESRGAN implementation (anime model)
│   │   ├── waifu2x.py      # waifu2x with noise reduction
│   │   └── lanczos.py      # Simple PIL fallback
│   ├── potrace_tracer.py   # Bitmap→SVG tracing (potracer wrapper)
│   ├── inkscape_wrapper.py # SVG→PNG rasterization
│   ├── image_comparer.py   # Binary SSIM quality scoring
│   ├── parameter_optimizer.py  # Sequential binary search
│   └── visual_logger.py    # Comparison sheet generation
├── svg_optimize.py         # Convenience wrapper script
├── ssim_tester.py          # Standalone SSIM testing tool
├── requirements.txt        # Core Python dependencies
├── requirements-cpu.txt    # CPU-only installation (includes core)
├── requirements-gpu.txt    # GPU installation (includes core)
├── PLANNING.md             # Detailed design documentation
└── README.md               # This file
```

## Tools

### SSIM Tester

A standalone tool for calibrating what SSIM scores mean for your specific use case:

```bash
python ssim_tester.py original.png manually_traced.svg
```

This helps you understand what scores to expect and validates that the optimizer is working correctly.

**Workflow:**

1. Manually trace an image in Inkscape with settings you like
2. Run the tester to see what score that gets
3. Use that as your quality reference

## Design Principles

This project follows strict coding principles:

- **DRY (Don't Repeat Yourself)** - Unified logging system, single source of truth
- **Separation of Concerns** - Each module has ONE job, clear boundaries
- **Small Files** - Every file is focused and manageable
- **Always Verbose** - Progress updates, never silent, constant feedback

## Technical Details

### Dependencies

**Core (always required):**

- **Pillow** - Image loading and manipulation
- **potracer** - Pure Python potrace implementation (bitmap tracing)
- **NumPy** - Array operations
- **scikit-image** - SSIM calculation
- **opencv-contrib-python-headless** - Noise analysis and contrib modules without GUI dependencies
- **svgelements** - SVG vector shape, curve, and transform parsing
- **Shapely** - Vector border offsets, smoothing, and enclosure checks
- **Rich** - Beautiful console output with progress bars

**Optional (for AI features):**

- **PyTorch** - Deep learning framework (CPU or CUDA)
- **Real-ESRGAN** - AI upscaling for line art (uses anime/illustration model)
- **waifu2x** - AI upscaling with noise reduction (specialized for line art)
- **rembg** - AI background removal (future feature)
- **basicsr** - Basic image restoration toolkit

### Why Binary SSIM?

When comparing a color input image to a black-and-white SVG output, standard SSIM penalizes luminance differences even when shapes match perfectly. By thresholding both images to pure binary (0 or 255) before comparison, we measure shape similarity - which is what actually matters for CAD applications.

### Why Sequential Binary Search?

Potrace parameters are mostly **orthogonal** (independent):

- **Threshold** - Determines WHERE shapes are
- **Smooth** - Determines HOW they're represented
- **Turdsize** - Just removes noise (set once, not optimized)

Since they affect different aspects, we can optimize them sequentially instead of testing every combination. This is both faster AND finds better results (adaptive precision vs fixed grid spacing).

## Contributing

Contributions welcome! This project emphasizes clean, maintainable code. Please follow the existing patterns:

- Small, focused files
- Comprehensive docstrings
- DRY principles
- Type hints where helpful

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with [potracer](https://github.com/tatarize/potrace) - Pure Python potrace implementation
- Uses [Inkscape](https://inkscape.org/) for SVG rasterization
- Inspired by the need for better bitmap→CAD workflows
