import cv2
import numpy as np
from PIL import Image

def compute_noise_metrics(image: np.ndarray):
    """Compute noise metrics."""
    img = image.astype(np.float32)
    
    # Laplacian variance
    laplacian = cv2.Laplacian(img, cv2.CV_32F)
    laplacian_variance = laplacian.var()
    
    # Noise residual
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    residual = img - blurred
    residual_std = residual.std()
    
    # Combined
    noise_score = laplacian_variance * 0.7 + residual_std * 0.3
    
    return {
        "laplacian_variance": laplacian_variance,
        "residual_std": residual_std,
        "noise_score": noise_score,
    }

# Test 1: Clean line art (white background, black lines)
clean = np.ones((100, 100), dtype=np.uint8) * 255
clean[10:20, :] = 0  # Horizontal line
clean[:, 10:20] = 0  # Vertical line

# Test 2: Noisy line art
noisy = clean.copy().astype(np.float32)
noise = np.random.normal(0, 10, noisy.shape)
noisy = np.clip(noisy + noise, 0, 255).astype(np.uint8)

# Test 3: Solid white (no noise, no edges)
solid = np.ones((100, 100), dtype=np.uint8) * 255

print("Clean line art:", compute_noise_metrics(clean))
print("Noisy line art:", compute_noise_metrics(noisy))
print("Solid white:", compute_noise_metrics(solid))