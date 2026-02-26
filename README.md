# SVG Auto-Optimizer

[![PyPI version](https://badge.fury.io/py/svg-auto-optimizer.svg)](https://badge.fury.io/py/svg-auto-optimizer)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically optimize bitmap-to-SVG conversion parameters using intelligent binary search and SSIM-based quality scoring.

## Overview

SVG Auto-Optimizer takes the guesswork out of converting raster images (PNG, JPG, etc.) to vector SVGs. Instead of manually tweaking Potrace parameters in Inkscape until it "looks right," this tool automatically finds the optimal settings for your specific image.

**Key Features:**

- 🎯 **Smart optimization** - Sequential binary search instead of brute-force grid search
- 📊 **Quality scoring** - Binary SSIM comparison measures shape accuracy, not color
- 🚀 **Fast convergence** - Typically 14-18 evaluations vs 20-30+ for grid search
- 📸 **Visual proof sheets** - See all tested combinations in a comparison grid
- ⏭️ **Bail-early** - Skips optimization if defaults already score 0.95+

**Perfect for:**

- Converting logos and line art for CAD software (Fusion 360, etc.)
- Preparing vector graphics from scanned drawings
- Batch processing images with consistent quality

## Installation

### Prerequisites

- Python 3.8+
- [Inkscape](https://inkscape.org/) installed and accessible from command line

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

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
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
                               [-v] [--log-file LOG_FILE]
                               input

positional arguments:
  input                 Input raster image (PNG, JPG, etc.)

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output SVG file path (default: input.svg)
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
- **OpenCV** - Noise analysis
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
