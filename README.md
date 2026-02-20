# SVG Auto-Optimizer

Automatically optimize bitmap-to-SVG conversion parameters by testing multiple combinations and selecting the best result based on visual similarity.

## 🚧 Current Status: Phase 1 - Foundation

We're building this step-by-step! Here's what's working now:

✅ **Core infrastructure** - config, unified logging system  
✅ **SSIM testing script** - Test image quality empirically  
🚧 **Main optimizer** - Coming next!

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Inkscape Installation

Make sure Inkscape is installed at:

```text
C:\Program Files\Inkscape\bin\inkscape.exe
```

If it's somewhere else, update `INKSCAPE_PATH` in `svg_optimizer/config.py`

## Current Tools

### SVG Auto-Optimizer (Main Application)

**Purpose:** Automatically optimize bitmap-to-SVG conversion by testing parameter combinations and selecting the best result.

**How it works:**

1. Analyzes your image (noise level, background type)
2. Tries default parameters first
3. If defaults aren't good enough, runs sequential binary search optimization
4. Saves the best SVG it finds!

**Basic Usage:**

```bash
# Simple - optimize and save as input.svg
python -m svg_optimizer logo.png

# Or use the wrapper script
python svg_optimize.py logo.png

# Specify custom output location
python -m svg_optimizer logo.png --output my_logo.svg

# Skip optimization, just use defaults (fast!)
python -m svg_optimizer logo.png --skip-optimization

# Manual threshold override
python -m svg_optimizer logo.png --threshold 0.35

# Verbose debug output
python -m svg_optimizer logo.png --verbose
```

**What it does:**

- ✅ Analyzes image (noise, background type)
- ✅ Tests defaults first (might be good enough!)
- ✅ Binary search optimization if needed (Phase 1: threshold, Phase 2: smooth)
- ✅ Saves optimized SVG
- ✅ Shows final parameters and SSIM score
- ✅ Progress bars and status updates throughout!

**Example Output:**

```text
================================================================
SVG Auto-Optimizer
================================================================
Input: logo.png
Output: logo.svg

Analyzing image characteristics...
  Dimensions: 512x512 pixels
  Noise level: LOW (score=23.4)
  Background: LIGHT (brightness=0.89)

================================================================
Testing Default Parameters
================================================================
Default parameters: threshold=0.450, turdsize=2, smooth=1.00
Default SSIM score: 0.8834
⚠ Score 0.8834 below threshold (0.95)
Starting parameter optimization...

================================================================
Binary Search: threshold
================================================================
Starting at 0.450, step=0.200
  ↓ Improved to 0.350 (score=0.9123, +0.0289)
  ↓ Improved to 0.250 (score=0.9401, +0.0278)
  Peaked! Halving step to 0.100
Converged after 8 iterations
Best threshold: 0.280 (score=0.9456)

================================================================
Binary Search: smooth
================================================================
Starting at 1.000, step=0.300
  ↑ Improved to 1.100 (score=0.9489, +0.0033)
Converged after 5 iterations
Best smooth: 1.120 (score=0.9492)

================================================================
Optimization Complete!
================================================================
✓ Saved SVG: logo.svg
Final parameters:
  Threshold: 0.280
  Smooth: 1.12
  Turdsize: 2
Final SSIM score: 0.9492
Improvement: +0.0658
Total evaluations: 13
Time: 8.3s
```

### SSIM Tester

**Purpose:** Figure out what SSIM score means "good enough" for YOUR images.

**Workflow:**

1. Manually convert an image to SVG in Inkscape using settings you like
2. Run the SSIM tester to see how well it scores
3. Try different Inkscape settings and re-test
4. Determine your "acceptable" SSIM threshold

**Usage:**

```bash
python ssim_tester.py my_image.png my_image.svg
```

**Example:**

```bash
# You manually created logo.svg from logo.png in Inkscape
python ssim_tester.py logo.png logo.svg

# Output will show:
# SSIM Score: 0.9234
# Assessment: VERY GOOD - Likely acceptable
```

**What the scores mean:**

- `0.95+` = Excellent (optimizer would skip optimization)
- `0.90-0.95` = Very good
- `0.85-0.90` = Good
- `0.80-0.85` = OK
- `<0.80` = Poor (definitely needs optimization)

## Project Structure

```text
svg_optimizer/
├── __init__.py          # Package initialization
├── config.py            # All constants and settings (EDIT THIS!)
└── utils.py             # Unified logging and helpers

ssim_tester.py           # Standalone SSIM testing tool
requirements.txt         # Python dependencies
PLANNING.md             # Full project design document
```

## Design Principles

This codebase follows strict design principles:

✅ **Small, focused files** - Each module does ONE thing  
✅ **Separation of Concerns** - Clear boundaries between components  
✅ **DRY** - Never repeat yourself (especially logging!)  
✅ **Always verbose** - The app is NEVER silent

### The Unified Logging System

We use a special logging approach where **one call logs to BOTH file and console**:

```python
# WRONG (violates DRY):
console.print("Starting...")
logger.info("Starting...")

# RIGHT (one call, two outputs):
log_info("Starting...")
```

All logging functions are in `utils.py` and automatically:

- Write to `svg_optimizer.log` (Python logging)
- Display pretty output via Rich (console)

## Next Steps

We're building this incrementally! Next up:

- [ ] Potrace tracer module
- [ ] Inkscape wrapper for rasterization
- [ ] Image comparison and analysis
- [ ] Parameter grid generator
- [ ] Main optimization loop
- [ ] Visual comparison sheet generator

Stay tuned! 🚀
