# SVG Auto-Optimizer

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

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/svg-optimizer.git
cd svg-optimizer
```

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

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

# Skip optimization, just use defaults (fast!)
python -m svg_optimizer logo.png --skip-optimization

# Manual threshold override
python -m svg_optimizer logo.png --threshold 0.35

# Skip the comparison sheet
python -m svg_optimizer logo.png --no-comparison

# Verbose debug output
python -m svg_optimizer logo.png --verbose
```

### Full Options

```text
usage: python -m svg_optimizer [-h] [-o OUTPUT] [-c COMPARISON] [--no-comparison]
                               [--skip-optimization] [--threshold THRESHOLD]
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
  -v, --verbose         Enable verbose debug output
  --log-file LOG_FILE   Custom log file path (default: svg_optimizer.log)
```

## How It Works

### 1. Image Analysis

Analyzes your input image to determine:

- **Noise level** - How much speckle removal is needed
- **Background type** - Light vs dark (affects threshold search range)

### 2. Try Defaults First

Tests Inkscape's default parameters (threshold=0.45, smooth=1.0). If the SSIM score is ≥0.95, optimization is skipped entirely!

### 3. Sequential Binary Search Optimization

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

### 4. Generate Outputs

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
│   ├── image_analysis.py   # Noise & background detection
│   ├── potrace_tracer.py   # Bitmap→SVG tracing (potracer wrapper)
│   ├── inkscape_wrapper.py # SVG→PNG rasterization
│   ├── image_comparer.py   # Binary SSIM quality scoring
│   ├── parameter_optimizer.py  # Sequential binary search
│   └── visual_logger.py    # Comparison sheet generation
├── svg_optimize.py         # Convenience wrapper script
├── ssim_tester.py          # Standalone SSIM testing tool
├── requirements.txt        # Python dependencies
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

- **Pillow** - Image loading and manipulation
- **potracer** - Pure Python potrace implementation (bitmap tracing)
- **NumPy** - Array operations
- **scikit-image** - SSIM calculation
- **OpenCV** - Noise analysis
- **Rich** - Beautiful console output with progress bars

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
