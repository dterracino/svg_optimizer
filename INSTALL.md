# Installation Guide

Complete installation instructions for svg-auto-optimizer with GPU/CPU support.

**Quick Navigation:**

- [Quick Start (Core Only)](#quick-start-core-features-only) - Basic SVG without AI
- [Critical Requirements](#critical-installation-issues--solutions) - **READ THIS FIRST** to avoid common issues
- [GPU Installation](#gpu-installation-nvidia-cuda) - Full AI features with CUDA
- [CPU Installation](#cpu-installation-no-gpu) - AI features on CPU (slower)
- [waifu2x Installation](#waifu2x-installation-optional) - Optional upscaler
- [Troubleshooting](#additional-troubleshooting) - When things go wrong
- [Real-World Timeline](#real-world-installation-timeline) - What we learned during testing

**⚠️ IMPORTANT:** If you want AI upscaling features, you **MUST** use Python 3.11 (not 3.12 or 3.13). See [Critical Issues](#critical-installation-issues--solutions) for why.

---

## Quick Reference

**I just want it to work with AI upscaling:**

```bash
# 1. Ensure Python 3.11 (CHECK THIS FIRST!)
python --version  # Must be 3.11.x

# 2. Create venv and install
python -m venv .venv
.venv\Scripts\activate  # Windows
python -m pip install --upgrade pip
pip install -r requirements-gpu.txt  # or requirements-cpu.txt
```

**I have Python 3.12 and getting errors:**

```bash
# Install Python 3.11 from python.org first, then:
py -3.11 -m venv .venv  # Windows
.venv\Scripts\activate
pip install -r requirements-gpu.txt
```

**I want everything (GPU + Real-ESRGAN + waifu2x):**

```bash
# 1. Install GPU dependencies (Python 3.11)
pip install -r requirements-gpu.txt

# 2. Download waifu2x binary
# From: https://github.com/nihui/waifu2x-ncnn-vulkan/releases
# Extract to: tools/waifu2x-ncnn-vulkan/
```

**It's broken, start over:**

```bash
# Clean slate (see Clean Reinstall section)
rm -rf .venv
py -3.11 -m venv .venv  # Ensure Python 3.11
.venv\Scripts\activate
python --version  # Verify 3.11.x
pip install -r requirements-gpu.txt
```

---

## Quick Start (Core Features Only)

```bash
pip install svg-auto-optimizer
```

This gives you basic SVG optimization without AI upscaling.

## Full Installation with AI Upscaling

### Prerequisites

1. **Python 3.11** - REQUIRED for AI upscaling (PyTorch 2.1.x compatibility)
   - Check with `python --version`
   - ⚠️ **Python 3.12+ will NOT work** - PyTorch 2.1.x only has wheels for cp38-cp311
   - Download Python 3.11.x from [python.org](https://www.python.org/downloads/)
   - On Windows with multiple Python versions: Use `py -3.11 -m venv .venv`
2. **Inkscape** - Must be accessible from command line
   - Windows: Install from [inkscape.org](https://inkscape.org/) and ensure it's in PATH
   - Linux: `sudo apt install inkscape`
   - Mac: `brew install inkscape`
3. **Git** (for installing from source)

### GPU Installation (NVIDIA CUDA)

**Requirements:**

- **Python 3.11** (not 3.12+) - See Prerequisites above
- NVIDIA GPU with CUDA support
- CUDA 12.1+ drivers installed

**Steps:**

```bash
# 1. Create virtual environment with Python 3.11
# Windows (if multiple Python versions installed):
py -3.11 -m venv .venv
# OR if Python 3.11 is your default:
python -m venv .venv

# 2. Activate it
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Verify Python version (MUST be 3.11.x)
python --version

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install requirements (includes PyTorch 2.1.2+cu121)
pip install -r requirements-gpu.txt

# OR if installing from PyPI:
pip install svg-auto-optimizer[gpu]
```

**What gets installed:**

- PyTorch 2.1.2+cu121 (last version before breaking changes)
- torchvision 0.16.2+cu121 (matched version)
- Real-ESRGAN (AI upscaler with auto-downloading models)
- basicsr/facexlib (super-resolution libraries)
- rembg[gpu] (background removal)
- All core dependencies

### CPU Installation (No GPU)

**Requirements:**

- **Python 3.11** (not 3.12+) - See Prerequisites above

**Steps:**

```bash
# 1. Create virtual environment with Python 3.11
# Windows (if multiple Python versions installed):
py -3.11 -m venv .venv
# OR if Python 3.11 is your default:
python -m venv .venv

# 2. Activate it
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Verify Python version (MUST be 3.11.x)
python --version

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install requirements
pip install -r requirements-cpu.txt

# OR if installing from PyPI:
pip install svg-auto-optimizer[cpu]
```

**What gets installed:**

- PyTorch 2.1.2 CPU-only (last version before breaking changes)
- torchvision 0.16.2 CPU-only (matched version)
- Real-ESRGAN CPU support (slower but works)
- rembg[cpu] (background removal)

### waifu2x Installation (Optional)

waifu2x uses a native executable instead of a Python package for better performance and reliability.

**Why native executable?**

- The Python package `waifu2x-ncnn-vulkan-python` has build/compatibility issues
- Native binary is faster, more stable, and easier to install
- Works with Vulkan GPU acceleration (NVIDIA, AMD, Intel)

**Installation Steps:**

1. **Download** the latest release for your platform:
   - [waifu2x-ncnn-vulkan releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases)
   - Windows: Download `waifu2x-ncnn-vulkan-YYYYMMDD-windows.zip`
   - Linux: Download `waifu2x-ncnn-vulkan-YYYYMMDD-ubuntu.zip`
   - macOS: Download `waifu2x-ncnn-vulkan-YYYYMMDD-macos.zip`

2. **Extract** to `tools/waifu2x-ncnn-vulkan/` in the repository:

   ```
   svg_optimizer/              <- Repository root
     tools/
       waifu2x-ncnn-vulkan/
         waifu2x-ncnn-vulkan.exe   (or waifu2x-ncnn-vulkan on Linux/Mac)
         models-cunet/
         models-upconv_7_anime_style_art_rgb/
         models-upconv_7_photo/
         vcomp140.dll              (Windows only)
   ```

3. **Alternative - Add to PATH:**
   - Extract anywhere and add the folder to your system PATH
   - The tool will automatically find it in: PATH → ./tools/waifu2x-ncnn-vulkan/ → current directory

4. **Verify:**

   ```bash
   # Test if waifu2x is found
   python -c "from svg_optimizer.upscalers.waifu2x import Waifu2xUpscaler; u = Waifu2xUpscaler(); print('✓ Found' if u.initialize() else '✗ Not found')"
   ```

**Note:** waifu2x is optional. Real-ESRGAN and Lanczos are available without it.

## Verifying Installation

### Test Core Functionality

```bash
svg-optimizer --version
svg-optimizer --help
```

### Test AI Upscalers

Run this to see which upscalers are available:

```bash
python -c "from svg_optimizer.image_upscaler import ImageUpscaler; upscaler = ImageUpscaler(); print(upscaler.get_available_methods())"
```

Expected output:

- **GPU installation with waifu2x**: `['realesrgan', 'waifu2x', 'lanczos']`
- **GPU installation without waifu2x**: `['realesrgan', 'lanczos']`
- **CPU installation**: `['realesrgan', 'lanczos']` (Real-ESRGAN works on CPU, just slower)
- **Core only (no extras)**: `['lanczos']` (fallback only)

### Test Real-ESRGAN

```bash
python -c "from svg_optimizer.upscalers.realesrgan import RealESRGANUpscaler; u = RealESRGANUpscaler(); print('✓ Real-ESRGAN OK' if u.initialize() else '✗ Failed')"
```

**First run:** Model will auto-download to `~/.cache/realesrgan/` (220MB)

### Test waifu2x

```bash
python -c "from svg_optimizer.upscalers.waifu2x import Waifu2xUpscaler; u = Waifu2xUpscaler(); print('✓ waifu2x OK' if u.initialize() else '✗ Not found - see waifu2x Installation section')"
```

### Full Test

```bash
# Test with actual image (should produce SVG + comparison sheet)
python -m svg_optimizer samples/orangeblue.png --upscale
```

Expected behavior:

- Detects GPU/CPU
- Downloads Real-ESRGAN model on first run (if not cached)
- Upscales 2x using Real-ESRGAN
- Traces to SVG with optimized parameters
- Generates comparison sheet
- Exit code: 0

## Critical Installation Issues & Solutions

**TL;DR - What Actually Works (April 2026):**

- ✅ Real-ESRGAN **WORKS** (with correct setup)
- ✅ waifu2x **WORKS** (using native binary, not Python package)
- ⚠️ **Python 3.11 REQUIRED** (3.12+ will fail)
- ⚠️ PyTorch 2.1.2 specifically needed (2.2+ breaks compatibility)

### Issue 1: Python 3.12 Incompatibility ⚠️

**Error when installing:**

```
ERROR: Could not find a version that satisfies the requirement torch==2.1.2+cu121
```

**Root Cause:**

- PyTorch 2.1.x only has wheels for cp38, cp39, cp310, cp311 (not cp312)
- You're using Python 3.12, which is too new

**Solution:**

```bash
# Check your Python version
python --version

# If it says 3.12.x, you need Python 3.11
# Download Python 3.11.x from python.org

# On Windows with multiple versions, create venv with:
py -3.11 -m venv .venv

# On Linux:
# Use deadsnakes PPA for Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
python3.11 -m venv .venv
```

**Why This Happens:**
PyTorch 2.2+ removed the `torchvision.transforms.functional_tensor` module that basicsr/realesrgan depend on. We need PyTorch 2.1.2 for compatibility, but it doesn't support Python 3.12.

---

### Issue 2: PyTorch Index URL Configuration

**Error:**

```
ERROR: Could not find a version that satisfies the requirement pillow
ERROR: Could not find a version that satisfies the requirement numpy
```

**Root Cause:**
Using `--index-url` instead of `--extra-index-url` in requirements file blocks access to PyPI.

**Solution:**
Ensure `requirements-gpu.txt` uses `--extra-index-url`:

```
--extra-index-url https://download.pytorch.org/whl/cu121
torch==2.1.2+cu121
torchvision==0.16.2+cu121
```

**Not this** (blocks PyPI):

```
--index-url https://download.pytorch.org/whl/cu121  ❌
```

---

### Issue 3: Real-ESRGAN Model Not Found

**Error:**

```
FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\.../.cache/realesrgan/RealESRGAN_x4plus_anime_6B.pth'
```

**Root Cause:**
Older versions didn't auto-download the model file.

**Solution:**
Current version auto-downloads on first use. If you still see this error:

```bash
# Manual download
mkdir -p ~/.cache/realesrgan  # Linux/Mac
# or
New-Item -ItemType Directory -Force "$env:USERPROFILE\.cache\realesrgan"  # PowerShell

# Download model (220MB)
# Linux/Mac:
curl -L https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/RealESRGAN_x4plus_anime_6B.pth \
     -o ~/.cache/realesrgan/RealESRGAN_x4plus_anime_6B.pth

# Windows PowerShell:
Invoke-WebRequest -Uri "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/RealESRGAN_x4plus_anime_6B.pth" `
    -OutFile "$env:USERPROFILE\.cache\realesrgan\RealESRGAN_x4plus_anime_6B.pth"
```

---

### Issue 4: Deprecation Warning from basicsr

**Warning:**

```
DeprecationWarning: 'torchvision.transforms.functional_tensor' is deprecated and will be removed in a future version
```

**Root Cause:**
basicsr uses the deprecated module (still works but shows warning).

**Solution:**
Current version suppresses this warning automatically. If you still see it, update to the latest version.

**Manual fix** (already in code):

```python
import warnings
warnings.filterwarnings('ignore', message='.*torchvision.transforms.functional_tensor.*')
```

---

### Issue 5: waifu2x Python Package Build Failures

**Error:**

```
error: Microsoft Visual C++ 14.0 or greater is required
ERROR: Failed building wheel for waifu2x-ncnn-vulkan-python
```

**Root Cause:**
The Python package `waifu2x-ncnn-vulkan-python` requires compilation and often fails.

**Solution:**
We use the **native binary** instead (no compilation needed):

1. Download from [waifu2x-ncnn-vulkan releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases)
2. Extract to `tools/waifu2x-ncnn-vulkan/` or add to PATH
3. See "waifu2x Installation" section above

The code automatically finds the binary - no Python package needed!

## Additional Troubleshooting

### Check Your Environment

```bash
# Python version (must be 3.11.x for AI upscaling)
python --version

# Installed packages
pip list | grep -E "(torch|torchvision|realesrgan|basicsr|rembg)"
# Windows PowerShell:
pip list | Select-String "torch|torchvision|realesrgan|basicsr|rembg"

# GPU availability (if using CUDA)
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"

# CUDA version
nvidia-smi  # Shows driver version and CUDA version
```

Expected output for working GPU install:

```
Python 3.11.x
torch 2.1.2+cu121
torchvision 0.16.2+cu121
basicsr 1.4.2
realesrgan 0.3.0
rembg 2.0.5x
CUDA available: True
GPU: NVIDIA GeForce RTX xxxx
```

### waifu2x Not Found

**Error:** `waifu2x-ncnn-vulkan not found`

**Cause:** waifu2x binary not installed or not in PATH.

**Solution:**

1. Download from [waifu2x-ncnn-vulkan releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases)
2. Extract to `tools/waifu2x-ncnn-vulkan/` in the repository root, OR
3. Add the extracted folder to your system PATH

See the "waifu2x Installation" section above for detailed steps.

### CUDA Out of Memory

**Error:** `RuntimeError: CUDA out of memory`

**Solutions:**

1. **Reduce upscale factor:**

   ```bash
   svg-optimizer image.png --upscale --upscale-factor 2  # Instead of 4
   ```

2. **Use smaller model (waifu2x):**

   ```bash
   svg-optimizer image.png --upscale --upscale-method waifu2x
   ```

3. **Force CPU processing:**

   ```bash
   # Reinstall with CPU requirements
   pip install -r requirements-cpu.txt
   ```

Inkscape Not Found

**Error:** `Inkscape not found or not working`

**Solutions:**

1. **Install Inkscape:**
   - Windows: [inkscape.org](https://inkscape.org/) - use installer, check "Add to PATH"
   - Linux: `sudo apt install inkscape`
   - Mac: `brew install inkscape`

2. **Verify in PATH:**

   ```bash
   inkscape --version
   ```

3. **If installed but not in PATH:**
   - Windows: Add Inkscape bin folder to system PATH (usually `C:\Program Files\Inkscape\bin`)
   - Restart terminal after changing PATH

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'xxx'`

**Solution:**

```bash
# Ensure virtual environment is activated
# You should see (.venv) in your terminal prompt

# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# If still failing, reinstall dependencies
pip install --upgrade -r requirements-gpu.txt --force-reinstall
```

### Permission Errors

**Error:** `Permission denied` or `Access is denied`

**Solutions:**

1. **Use virtual environment** (not system-wide install)
2. **Run terminal as regular user** (don't need admin)
3. **Check antivirus** - may block pip operations
4. **Close other processes** using the same files

### Slow First Run

**Normal behavior:**

1. **First import of PyTorch:** 10-30 seconds (compiling CUDA kernels)
2. **First Real-ESRGAN run:** 30-60 seconds (downloading 220MB model)
3. **Subsequent runs:** Should be much faster (model cached)

**If consistently slow:**

- Check GPU is actually being used (see "Check Your Environment" above)
- May be using CPU fallback Lanczos Fallback Warning

**Warning:** `Using Lanczos 2x (PIL fallback) - AI upscalers not available`

**Meaning:** GPU dependencies aren't installed. This still works but uses basic interpolation instead of AI.

**Fix:** Install with GPU or CPU extras:

```bash
pip install svg-auto-optimizer[gpu]  # or [cpu]
```

## Development Installation

For contributing or testing:

```bash
# Clone the repo
git clone https://github.com/dterracino/svg_optimizer.git
cd svg_optimizer

# Create venv
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install with dev tools
pip install -r requirements-gpu.txt  # or requirements-cpu.txt
pip install -e .  # Editable install

# Install dev dependencies
pip install pytest black flake8 mypy
```

## Updating

### From PyPI

```bash
pip install --upgrade svg-auto-optimizer
```

### From Source

```bash
git pull
pip install -r requirements-gpu.txt --upgrade
```

## Clean Reinstall

If everything is broken and you want to start fresh:

```bash
# 1. Deactivate current environment
deactivate  # or just close terminal

# 2. Remove virtual environment
# Windows PowerShell:
Remove-Item -Recurse -Force .venv
# Linux/Mac:
rm -rf .venv

# 3. Verify Python 3.11
python --version  # or py -3.11 --version

# 4. Create fresh venv with Python 3.11
# If you have multiple Python versions:
py -3.11 -m venv .venv  # Windows
python3.11 -m venv .venv  # Linux
# If Python 3.11 is your default:
python -m venv .venv

# 5. Activate
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 6. Verify it's Python 3.11.x
python --version

# 7. Upgrade pip
python -m pip install --upgrade pip

# 8. Install from scratch
pip install -r requirements-gpu.txt  # or requirements-cpu.txt

# 9. Verify installation
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

## Optional: System-Wide Installation

**Not recommended** - use virtual environments instead for isolation.

But if you really want to:

```bash
# No venv (installs globally)
# Requires Python 3.11
python -m pip install svg-auto-optimizer[gpu]

# Now available globally
svg-optimizer --version
```

**Risks:**

- Can conflict with other projects
- Harder to troubleshoot
- Difficult to uninstall cleanly
- May require admin/sudo

---

## Real-World Installation Timeline

This documents the actual issues encountered during development and testing:

### Initial Attempt (Python 3.12 - FAILED)

```
User environment: Python 3.12, Windows 11, NVIDIA RTX GPU
Command: pip install -r requirements-gpu.txt

❌ ERROR: Could not find a version that satisfies the requirement torch==2.1.2+cu121
Diagnosis: PyTorch 2.1.x doesn't have wheels for Python 3.12 (cp312)
```

### Second Attempt (Fixed Python version)

```
Action: Installed Python 3.11, created new venv
Command: py -3.11 -m venv .venv
         .venv\Scripts\activate
         pip install -r requirements-gpu.txt

❌ ERROR: No module named 'torchvision.transforms.functional_tensor'
Diagnosis: requirements-gpu.txt had wrong index URL syntax
```

### Third Attempt (Fixed index URL)

```
Action: Changed --index-url to --extra-index-url in requirements-gpu.txt
Command: pip install -r requirements-gpu.txt

✅ SUCCESS: All packages installed
PyTorch 2.1.2+cu121, torchvision 0.16.2+cu121, basicsr, realesrgan all OK
```

### Fourth Attempt (First run test)

```
Command: python -m svg_optimizer samples/orangeblue.png --upscale

❌ ERROR: FileNotFoundError: RealESRGAN_x4plus_anime_6B.pth not found
Diagnosis: Model file not auto-downloading
```

### Fifth Attempt (Fixed model download)

```
Action: Added urllib.request auto-download logic to realesrgan.py
Result: Model downloads on first run (220MB to ~/.cache/realesrgan/)

⚠️  WARNING: DeprecationWarning about functional_tensor
Diagnosis: basicsr imports the deprecated module (still works though)
```

### Sixth Attempt (Suppressed warning)

```
Action: Added warnings.filterwarnings to realesrgan.py
Command: python -m svg_optimizer samples/orangeblue.png --upscale

✅ SUCCESS: Everything works!
- GPU detected
- Real-ESRGAN model loaded
- Image upscaled 2x
- SVG traced with optimization
- Comparison sheet generated
- Exit code: 0
```

### waifu2x Journey (Parallel track)

```
Initial: Tried waifu2x-ncnn-vulkan-python package
❌ Build failures, requires MSVC, complex dependencies

Solution: Switched to native binary approach
1. Downloaded waifu2x-ncnn-vulkan-20220728-windows.zip
2. Extracted to tools/waifu2x-ncnn-vulkan/
3. Updated waifu2x.py to run subprocess instead of Python import

✅ Works perfectly, faster than Python package, no build needed
```

### Key Lessons Learned

1. **Python 3.11 is non-negotiable** for AI features (PyTorch 2.1.x limitation)
2. **--extra-index-url not --index-url** (must access both PyTorch and PyPI)
3. **PyTorch 2.1.2 specifically** (2.2+ breaks basicsr/realesrgan, older unavailable)
4. **Real-ESRGAN works fine** when versions are correct (not "broken" as initially thought)
5. **waifu2x binary > Python package** (easier install, better performance)
6. **Model auto-download needed** (220MB download on first run is expected)
7. **Warnings are cosmetic** (deprecation warning can be safely suppressed)

---

## Version Lock Explanation

You might wonder: "Why such specific versions?"

**The Dependency Chain:**

```
basicsr 1.4.2 (released 2021)
  └─ depends on: torchvision.transforms.functional_tensor
  
PyTorch timeline:
  2.1.2 (Dec 2023) - Has functional_tensor ✅ Last version with Python 3.11 support
  2.2.0 (Jan 2024) - Removed functional_tensor ❌ Breaks basicsr
  2.3.0+ (2024+)   - Not backward compatible ❌ 

Python support in PyTorch 2.1.x:
  cp38, cp39, cp310, cp311 ✅
  cp312 ❌ Not available

Result: Python 3.11 + PyTorch 2.1.2 is the ONLY working combination.
```

**Why not update basicsr?**

- Last release: 2021 (no active maintenance)
- realesrgan depends on it
- No PyTorch 2.2+ compatible fork available

**Will this break in the future?**

- PyTorch 2.1.2 wheels are archived and stable
- Works as of April 2026
- If PyTorch removes archive, we can host wheels ourselves

---

**Not recommended** - use virtual environments instead.

But if you really want to:

```bash
# No venv
pip install svg-auto-optimizer[gpu]

# Now available globally
svg-optimizer --version
```

## Platform-Specific Notes

### Windows

- Use PowerShell or Command Prompt (not Git Bash for activation)
- Antivirus may slow down first-time model downloads
- Inkscape installer usually adds to PATH automatically

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies
sudo apt update
sudo apt install python3-venv python3-pip inkscape

# NVIDIA drivers (for GPU)
sudo apt install nvidia-driver-535  # Or latest version

# Continue with installation above
```

### macOS

```bash
# Install Inkscape
brew install inkscape

# For M1/M2 Macs - CPU only (no CUDA)
pip install svg-auto-optimizer[cpu]
```

## Dependency Summary

### Core (Always Required)

- **Python 3.11** - Runtime (3.12+ NOT supported for AI features)
- Pillow - Image I/O
- potracer - SVG tracing
- numpy - Array operations
- scikit-image - SSIM comparison
- opencv-contrib-python-headless - Noise analysis and contrib modules without GUI dependencies
- rich - Console UI

### Optional (AI Upscaling - GPU)

- **torch 2.1.2+cu121** - Deep learning framework with CUDA 12.1
- **torchvision 0.16.2+cu121** - Image transforms (matched version)
- basicsr 1.4.2 - Super resolution base library
- facexlib - Face enhancement library (dependency of realesrgan)
- realesrgan 0.3.0 - Real-ESRGAN AI upscaler
- onnxruntime-gpu - ONNX Runtime with GPU support
- rembg[gpu] 2.0.50+ - Background removal with GPU

### Optional (AI Upscaling - CPU)

- **torch 2.1.2** - Deep learning framework (CPU-only)
- **torchvision 0.16.2** - Image transforms (CPU-only)
- basicsr 1.4.2 - Same as GPU but runs on CPU
- realesrgan 0.3.0 - Works on CPU (slower)
- onnxruntime - ONNX Runtime CPU
- rembg[cpu] 2.0.50+ - Background removal on CPU

### Optional (waifu2x)

- **waifu2x-ncnn-vulkan** - Native binary (not Python package)
  - Download from GitHub releases
  - Extract to tools/ or add to PATH
  - See "waifu2x Installation" section

### Why PyTorch 2.1.2?

**Critical:** PyTorch 2.2+ removed `torchvision.transforms.functional_tensor` module

- basicsr and realesrgan depend on this module
- PyTorch 2.1.2 is the last version that has it
- PyTorch 2.1.x only supports Python 3.8-3.11 (not 3.12+)
- We pin to 2.1.2+cu121 for GPU, 2.1.2 for CPU

This is why **Python 3.11 is mandatory** for AI features.

## Getting Help

If you're still having issues:

1. **Check Python version:**

   ```bash
   python --version
   # MUST be 3.11.x for AI features
   ```

2. **Check installed packages:**

   ```bash
   pip list | grep -E "(torch|realesrgan|basicsr)"
   # Windows: pip list | Select-String "torch|realesrgan|basicsr"
   ```

3. **Check CUDA/GPU (if using GPU):**

   ```bash
   nvidia-smi
   python -c "import torch; print('CUDA:', torch.cuda.is_available())"
   ```

4. **Run with verbose logging:**

   ```bash
   svg-optimizer image.png --verbose
   ```

5. **Try a simple test:**

   ```bash
   # Without AI (should always work):
   python -m svg_optimizer samples/orangeblue.png --skip-optimization
   
   # With AI:
   python -m svg_optimizer samples/orangeblue.png --upscale
   ```

6. **Check the Critical Issues section above** - most problems are covered there

7. **Open a GitHub issue** with:
   - Python version (`python --version`)
   - OS and version
   - Installed packages (`pip list`)
   - Full error message
   - Command you ran
   - Output of `--verbose` flag

## Common Success Patterns

**Pattern 1: Fresh Install (GPU)**

```bash
# Use Python 3.11
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-gpu.txt
# Works first time ✓
```

**Pattern 2: Fixing Python 3.12 Issue**

```bash
# Had Python 3.12, getting errors
# Installed Python 3.11 from python.org
py -3.11 -m venv .venv
.venv\Scripts\activate
python --version  # Verify: 3.11.x
pip install -r requirements-gpu.txt
# Now works ✓
```

**Pattern 3: Minimal Working Setup**

```bash
# Just want it to work, don't care about waifu2x
pip install -r requirements-gpu.txt
# Real-ESRGAN + Lanczos available ✓
# waifu2x optional
```

**Pattern 4: Complete Setup**

```bash
# Want everything
pip install -r requirements-gpu.txt
# Download waifu2x binary from GitHub
# Extract to tools/waifu2x-ncnn-vulkan/
# All 3 upscalers available ✓
```
