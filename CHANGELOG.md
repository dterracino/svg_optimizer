# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
