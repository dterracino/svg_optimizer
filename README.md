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
```
C:\Program Files\Inkscape\bin\inkscape.exe
```

If it's somewhere else, update `INKSCAPE_PATH` in `svg_optimizer/config.py`

## Current Tools

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

```
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
