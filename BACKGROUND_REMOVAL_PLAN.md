# Background Removal Implementation Plan

## Overview

Add AI-powered background removal using rembg library before SVG tracing. This will allow automatic extraction of foreground objects from images with complex backgrounds, improving SVG quality for logos, illustrations, and product photography.

## Model Selection Strategy

### Available Models (by Use Case)

#### General Purpose

- **u2net** - Default, best quality for most images (176MB)
- **u2netp** - Lightweight version (4.7MB)
- **silueta** - Reduced size u2net (43MB)
- **isnet-general-use** - Newer general-purpose model
- **birefnet-general** - State-of-the-art general model
- **birefnet-general-lite** - Lightweight BiRefNet
- **bria-rmbg** - BRIA AI state-of-the-art (recommended for production)

#### Specialized Models

- **u2net_human_seg** - Human portraits and people
- **birefnet-portrait** - Enhanced human portraits
- **u2net_cloth_seg** - Clothing/fashion (3 categories: upper/lower/full body)
- **isnet-anime** - High-accuracy anime character segmentation
- **birefnet-dis** - Dichotomous image segmentation
- **birefnet-hrsod** - High-resolution salient objects
- **birefnet-cod** - Concealed object detection
- **birefnet-massive** - Trained on massive dataset

#### Advanced

- **sam** - Segment Anything Model (requires point/box prompts)

### Recommended Default Strategy

```
auto (default) → Try models in this order:
  1. birefnet-general (best quality, modern)
  2. u2net (fallback, widely tested)
  3. u2netp (if memory constrained)
```

## CLI Interface Design

### Command Line Arguments

```bash
# Enable background removal with auto model selection
svg-optimizer input.png --remove-bg

# Specify model explicitly
svg-optimizer input.png --remove-bg --bg-model u2net_human_seg

# Background removal + upscaling
svg-optimizer input.png --remove-bg --upscale

# Advanced: alpha matting for better edge quality
svg-optimizer input.png --remove-bg --bg-alpha-matting

# Advanced: return only the mask (for debugging)
svg-optimizer input.png --remove-bg --bg-only-mask

# Advanced: post-processing parameters
svg-optimizer input.png --remove-bg --bg-post-process-mask
```

### CLI Arguments to Add (cli.py)

```python
parser.add_argument(
    '--remove-bg',
    action='store_true',
    help='Remove background before tracing (AI-powered)'
)

parser.add_argument(
    '--bg-model',
    type=str,
    choices=[
        'auto', 'u2net', 'u2netp', 'u2net_human_seg', 'u2net_cloth_seg',
        'silueta', 'isnet-general-use', 'isnet-anime',
        'birefnet-general', 'birefnet-general-lite', 'birefnet-portrait',
        'birefnet-dis', 'birefnet-hrsod', 'birefnet-cod', 'birefnet-massive',
        'bria-rmbg', 'sam'
    ],
    default='auto',
    help='Background removal model (default: auto - tries birefnet-general first)'
)

parser.add_argument(
    '--bg-alpha-matting',
    action='store_true',
    help='Apply alpha matting for smoother edges (slower but higher quality)'
)

parser.add_argument(
    '--bg-only-mask',
    action='store_true',
    help='Output only the mask instead of removed background (debug/preview)'
)

parser.add_argument(
    '--bg-post-process-mask',
    action='store_true',
    help='Apply post-processing to the mask for cleaner edges'
)
```

## Module Architecture

### File: `svg_optimizer/background_remover.py`

```python
"""
Background Removal Module - AI-powered background removal for cleaner tracing.

Uses rembg library with multiple model support for different use cases:
- General purpose (u2net, birefnet-general, bria-rmbg)
- Human portraits (u2net_human_seg, birefnet-portrait)
- Anime/illustrations (isnet-anime)
- Specialized (clothing, high-res, concealed objects)
"""
import warnings
from pathlib import Path
from typing import Optional, Literal
from PIL import Image

from . import log_info, log_success, log_warning, log_error, log_debug, log_section


# Model selection order for 'auto' mode
AUTO_MODEL_PRIORITY = [
    'birefnet-general',  # Best quality, modern architecture
    'u2net',             # Widely tested fallback
    'u2netp',            # Lightweight fallback
]


def detect_rembg_available() -> bool:
    """
    Check if rembg is available.
    
    Returns:
        True if rembg can be imported
    """
    try:
        import rembg
        return True
    except ImportError:
        return False


def remove_background(
    input_path: Path,
    output_path: Optional[Path] = None,
    model: str = 'auto',
    alpha_matting: bool = False,
    only_mask: bool = False,
    post_process_mask: bool = False,
) -> Optional[Path]:
    """
    Remove background from image using AI.
    
    Args:
        input_path: Path to input image
        output_path: Path to save result (None = create temp file)
        model: Model name or 'auto' for automatic selection
        alpha_matting: Apply alpha matting for smoother edges
        only_mask: Return only the mask instead of removed background
        post_process_mask: Apply post-processing to mask
    
    Returns:
        Path to output image, or None if failed
    """
    log_section("AI Background Removal")
    
    # Check if rembg is available
    if not detect_rembg_available():
        log_error("rembg not installed - cannot remove background")
        log_info("Install with: pip install -r requirements-gpu.txt")
        return None
    
    try:
        from rembg import remove, new_session
        
        # Load input image
        log_info(f"Loading image: {input_path}")
        input_image = Image.open(input_path)
        
        # Model selection
        models_to_try = AUTO_MODEL_PRIORITY if model == 'auto' else [model]
        
        session = None
        output_image = None
        
        for model_name in models_to_try:
            try:
                log_info(f"Trying model: {model_name}")
                
                # Create session (loads model)
                session = new_session(model_name)
                
                # Remove background
                output_image = remove(
                    input_image,
                    session=session,
                    alpha_matting=alpha_matting,
                    only_mask=only_mask,
                    post_process_mask=post_process_mask,
                )
                
                log_success(f"Background removed using {model_name}")
                break
                
            except Exception as e:
                log_warning(f"Model {model_name} failed: {e}")
                if model == 'auto' and model_name != models_to_try[-1]:
                    log_info("Trying next model...")
                    continue
                else:
                    raise
        
        if output_image is None:
            log_error("All models failed")
            return None
        
        # Save result
        if output_path is None:
            # Create temp file with '_nobg' suffix
            output_path = input_path.with_stem(input_path.stem + '_nobg')
        
        output_image.save(output_path)
        log_success(f"Saved: {output_path}")
        
        return output_path
        
    except ImportError as e:
        log_error(f"Missing dependencies: {e}")
        log_info("Install with: pip install -r requirements-gpu.txt")
        return None
        
    except Exception as e:
        log_error(f"Background removal failed: {e}")
        import traceback
        log_debug(traceback.format_exc())
        return None


def get_model_recommendation(image_path: Path) -> str:
    """
    Analyze image and recommend best background removal model.
    
    THIS IS A FUTURE ENHANCEMENT - for now just returns 'auto'
    
    Could analyze:
    - Image size (high-res → birefnet-hrsod)
    - Content type (face detection → u2net_human_seg)
    - Color distribution (anime-style → isnet-anime)
    
    Args:
        image_path: Path to image
    
    Returns:
        Recommended model name
    """
    # TODO: Implement smart model selection based on image analysis
    return 'auto'
```

## Workflow Integration

### Current Workflow (from **main**.py)

```
1. Validate inputs
2. AI Upscaling (optional) → working_input
3. Analyze image
4. Initialize components
5. Try defaults
6. Optimize parameters
7. Generate comparison
```

### Proposed Workflow (Two Options)

#### Option A: Remove BG BEFORE upscaling (RECOMMENDED)

```
1. Validate inputs
2. AI Background Removal (optional) → working_input
3. AI Upscaling (optional) → working_input  
4. Analyze image
5. Initialize components
6. Try defaults
7. Optimize parameters
8. Generate comparison
```

**Pros:**

- Smaller file to upscale (just foreground)
- Faster upscaling
- Less memory usage
- Cleaner edges in final SVG

**Cons:**

- Low-res background removal might miss fine edge details

#### Option B: Remove BG AFTER upscaling

```
1. Validate inputs
2. AI Upscaling (optional) → working_input
3. AI Background Removal (optional) → working_input
4. Analyze image
5. Initialize components
6. Try defaults
7. Optimize parameters
8. Generate comparison
```

**Pros:**

- Higher resolution for more accurate background detection
- Better edge detail preservation

**Cons:**

- Slower (upscaling full image with background)
- More memory usage

**DECISION: Use Option A** (remove bg before upscaling) because:

- Most use cases are logos/icons where bg removal is the primary goal
- User can always upscale first externally if needed
- Performance matters for batch processing

### Integration Code (**main**.py modifications)

```python
# After Step 1: Validate Inputs

# ========================================================================
# Step 2: AI Background Removal (Optional)
# ========================================================================

bg_removed_temp_file = None

if args.remove_bg:
    try:
        from svg_optimizer.background_remover import remove_background
        
        bg_removed_path = remove_background(
            working_input,
            output_path=None,  # Create temp file
            model=args.bg_model,
            alpha_matting=args.bg_alpha_matting,
            only_mask=args.bg_only_mask,
            post_process_mask=args.bg_post_process_mask,
        )
        
        if bg_removed_path:
            working_input = bg_removed_path
            bg_removed_temp_file = bg_removed_path  # Track for cleanup
            log_info(f"Using background-removed image: {bg_removed_path}")
        else:
            log_warning("Background removal failed, using original image")
            
    except ImportError as e:
        log_error(f"Background removal dependencies not available: {e}")
        log_warning("Continuing with original image")
        log_info("To enable, install: pip install -r requirements-gpu.txt")
    except Exception as e:
        log_error(f"Unexpected error during background removal: {e}")
        log_warning("Continuing with original image")


# ========================================================================
# Step 3: AI Upscaling (Optional)
# ========================================================================

# ... existing upscaling code (uses working_input) ...
```

### Cleanup Code (at end of main())

```python
# Cleanup temp files
if bg_removed_temp_file and bg_removed_temp_file.exists():
    bg_removed_temp_file.unlink()
    log_debug(f"Cleaned up temp file: {bg_removed_temp_file}")
```

## Dependencies

Already installed in requirements-gpu.txt:

```
rembg[gpu]>=2.0.50
```

This includes:

- rembg - Core background removal
- onnxruntime-gpu - GPU acceleration
- Models auto-download to ~/.u2net/ on first use

## Testing Strategy

### Test Cases

1. **Basic functionality**
   - Simple logo with solid background → should remove cleanly
   - Photo with person → should extract person
   - Anime character → should use isnet-anime model

2. **Model selection**
   - `--bg-model auto` → uses birefnet-general
   - `--bg-model u2net_human_seg` → uses human segmentation
   - Invalid model name → error message

3. **Integration with upscaling**
   - `--remove-bg --upscale` → both work together
   - Order matters: bg removal then upscaling

4. **Edge cases**
   - Image already has transparent background → should preserve
   - Complex background → test edge quality
   - Low resolution input → test with/without upscaling first

5. **Error handling**
   - rembg not installed → graceful fallback
   - Model download fails → try next model
   - Out of memory → fallback to smaller model

### Test Files to Create

```python
# test_background_removal.py

def test_basic_removal():
    """Test basic background removal"""
    result = remove_background('samples/orangeblue.png', model='u2net')
    assert result is not None
    assert result.exists()

def test_auto_model_selection():
    """Test auto model selection tries multiple models"""
    result = remove_background('samples/orangeblue.png', model='auto')
    assert result is not None

def test_human_segmentation():
    """Test human-specific model"""
    result = remove_background('samples/person.jpg', model='u2net_human_seg')
    assert result is not None

def test_with_upscaling():
    """Test background removal + upscaling workflow"""
    # Remove bg first
    bg_removed = remove_background('samples/logo.png')
    # Then upscale
    upscaled = upscale_for_tracing(bg_removed, scale=2)
    assert upscaled is not None
```

## Documentation Updates

### README.md Updates

Add to "Features" section:

```markdown
- **AI Background Removal** - Automatic foreground extraction with 15+ specialized models
  - General purpose: birefnet-general, u2net, bria-rmbg
  - Human portraits: u2net_human_seg, birefnet-portrait  
  - Anime/illustrations: isnet-anime
  - Advanced: clothing segmentation, high-res objects, concealed detection
```

Add to "Usage Examples":

```markdown
# Remove background before tracing
python -m svg_optimizer logo.png --remove-bg

# Use human segmentation model for portraits
python -m svg_optimizer portrait.jpg --remove-bg --bg-model u2net_human_seg

# Remove background + upscale for best quality
python -m svg_optimizer low_res_logo.png --remove-bg --upscale --upscale-factor 4

# Alpha matting for smoother edges (slower)
python -m svg_optimizer product.png --remove-bg --bg-alpha-matting
```

### INSTALL.md Updates

Add note about model auto-download:

```markdown
## Background Removal Models

Background removal models are automatically downloaded on first use:
- Location: `~/.u2net/` (Linux/Mac) or `%USERPROFILE%\.u2net\` (Windows)
- Models range from 4MB (u2netp) to 176MB (u2net)
- First run will download the selected model
- Subsequent runs reuse cached models

To pre-download a specific model:
```bash
python -c "from rembg import new_session; new_session('u2net')"
```

```

## Implementation Checklist

- [ ] Create `svg_optimizer/background_remover.py` module
- [ ] Add CLI arguments to `svg_optimizer/cli.py`
- [ ] Integrate into workflow in `svg_optimizer/__main__.py`
- [ ] Add temp file cleanup for bg-removed images
- [ ] Update README.md with examples
- [ ] Update INSTALL.md with model info
- [ ] Create `test_background_removal.py` test suite
- [ ] Test with various image types (logo, photo, anime)
- [ ] Test all model types
- [ ] Test integration with upscaling
- [ ] Add logging for model selection process
- [ ] Document model recommendations for different use cases
- [ ] Add memory usage warnings for large models
- [ ] Consider adding progress callback for long operations

## Future Enhancements

1. **Smart Model Selection**
   - Analyze image content (face detection → human_seg)
   - Detect anime style → isnet-anime
   - High resolution → birefnet-hrsod

2. **SAM Integration**
   - Interactive point/box selection for SAM model
   - GUI mode for selecting foreground regions

3. **Batch Processing Optimization**
   - Reuse session across multiple images
   - Model caching to avoid reloading

4. **Quality Metrics**
   - Estimate background removal quality
   - Warn if edges are poor quality

5. **Integration with Comparison Sheet**
   - Show before/after background removal
   - Show mask overlay for debugging

6. **Background Replacement**
   - `--bg-color` to replace with solid color instead of transparent
   - `--bg-image` to composite onto new background

## Notes

- rembg uses ONNX Runtime (already installed for GPU support)
- All models are in ONNX format, no PyTorch dependency for inference
- GPU acceleration works automatically with onnxruntime-gpu
- Models are cached, only downloaded once
- Performance: ~0.5-2 seconds per image depending on model and GPU

## References

- rembg GitHub: https://github.com/danielgatis/rembg
- Model details: https://github.com/danielgatis/rembg#models
- BiRefNet paper: Best performing model for general use
- U-2-Net paper: Original widely-used architecture
