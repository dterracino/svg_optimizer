# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- Removed the `box` border-type alias from the CLI and library. Use `frame` instead.

## [0.2.0] - 2026-10-09

### Added

- `--border-type` / `--border-style` for smooth `outline` borders and bounding-box `frame` borders, with optional unit-aware `--corner-radius`.
- `--border-units` for physical distances (`mm`, `cm`, `in`, `px`, `pt`, `pc`) and percentages of the shorter SVG canvas side, while retaining SVG user-unit compatibility and automatic omitted defaults.
- Early border curve-budget preflight before flattening and buffering, with actionable errors for excessive detail.
- `--border` to enable scale-aware automatic distances; omitted CLI smoothing, tolerance, and stroke width now scale with the SVG viewport, while explicit values remain unchanged.
- CLI border progress with stage names, activity spinner, per-stage elapsed time, processed counts, and visible cubic-fitting retries; optional for library callers.
- Vector-only `SVGBorderGenerator` for smooth enclosing borders with minimum artwork clearance.
- CLI border offset, smoothing radius, approximation tolerance, stroke width, and color options.
- Existing SVG input mode that preserves the source artwork and requires no Inkscape or rasterization.
- Optional borders on final bitmap-tracing outputs, without affecting optimization scores.
- Geometry and CLI regression tests for clearance, concavity, transforms, outliers, and unsupported SVG features.
- Border support for CorelDRAW rendering hints and simple embedded class-based presentation rules, preserving the original styles and artwork.

### Changed

- Rounded frames now validate clearance against actual artwork, allowing large corners in empty bounding-box regions and minimally expanding all sides when necessary without changing the requested radius.
- Outline smoothing now applies periodic Gaussian-weighted perimeter averaging before cubic fitting, suppressing fine bumps and notches while retaining validated enclosure, clearance, and smooth closing joins; frame borders are unchanged.
- Default bordered output filenames now include type and offset with units: `{filename}_border_{type}_{offset}{unit}.svg`, including automatic offsets and both raster output branches.
- Border output now uses closed cubic Bezier curves with continuous first and second derivatives, including at the closing seam, instead of straight-line polygons.
- Removed coarse border simplification; perimeter averaging smooths small details without creating faceted arcs.
- Enclosure and minimum-clearance checks now validate the fitted curves, with outward refitting when necessary and explicit failure for unsafe fits.
- Border canvas bounds now account for cubic control points and the full stroke.
- Replaced `opencv-python` with `opencv-contrib-python-headless` to include contrib modules without GUI dependencies.
- Added `svgelements` and Shapely dependencies for vector border processing.

### Compatibility Notes

- Border distances default to SVG user units; physical units and percentages are opt-in with `--border-units`.
- Omitted CLI border distances now use scale-aware defaults. Explicit distance values remain unchanged.
- Border output filenames now include type, offset, and unit; use `--output` to keep a specific destination.
- Rounded frames preserve the requested radius and may expand beyond the minimum offset to maintain artwork clearance.
- Python 3.11 is the documented target runtime for the pinned CPU/GPU upscaling dependencies.

## [0.1.0] - 2026-02-26

### Added

- Initial release of SVG Auto-Optimizer
- Automated bitmap-to-SVG conversion parameter optimization
- Sequential binary search optimization (faster than grid search)
- Binary SSIM-based quality scoring
- AI upscaling support (Real-ESRGAN, waifu2x, Lanczos)
- Automatic GPU detection and acceleration
- Image noise and background analysis
- Visual comparison sheet generation
- Rich console output with progress bars
- Comprehensive CLI with argparse
- Support for CPU-only and GPU installations
- Bail-early optimization (skips when defaults score ≥0.95)

### Features

- **Upscalers:**
  - Real-ESRGAN (anime/line art optimized model)
  - waifu2x with configurable noise reduction (0-3 levels)
  - Lanczos fallback for environments without AI libraries
  
- **Image Analysis:**
  - Automatic noise level detection
  - Background type detection (light vs dark)
  
- **Optimization:**
  - Two-phase sequential binary search (threshold, then smooth)
  - Typically converges in 14-18 iterations vs 20-30+ for grid search
  - Orthogonal parameter optimization for better results

- **Output:**
  - Optimized SVG files
  - Visual comparison sheets showing all tested combinations
  - Detailed logging with progress indicators

### Dependencies

- Core: Pillow, potracer, NumPy, scikit-image, OpenCV, Rich
- Optional: PyTorch, Real-ESRGAN, waifu2x, rembg, basicsr

### External Requirements

- Inkscape (must be installed and accessible from command line)

### Documentation

- Comprehensive README with usage examples
- Detailed PLANNING.md with design documentation
- Inline code documentation and docstrings
