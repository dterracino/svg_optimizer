from potrace import Bitmap
from PIL import Image
import sys

# Load your image
img = Image.open('huntrix.png').convert('L')
print(f"Image size: {img.size}")

# Create bitmap with default threshold
bm = Bitmap(img, blacklevel=0.45)
print(f"Bitmap created")

# Trace it
paths = bm.trace(
    turdsize=2,
    turnpolicy=4,
    alphamax=1.0,
    opticurve=True,
    opttolerance=0.2
)

print(f"Number of curves: {len(paths)}")
print(f"First few curves have this many segments:")
for i, curve in enumerate(paths[:5]):
    print(f"  Curve {i}: {len(curve.segments)} segments, start={curve.start_point}")
    
# Check if paths look reasonable
total_segments = sum(len(curve.segments) for curve in paths)
print(f"Total segments across all curves: {total_segments}")