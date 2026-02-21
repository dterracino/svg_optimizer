from potrace import Bitmap
from PIL import Image
import numpy as np

# Create circle to get curved segments
arr = np.zeros((50,50))
for i in range(50):
    for j in range(50):
        if (i-25)**2 + (j-25)**2 < 400:
            arr[i,j] = 255

img = Image.fromarray(arr.astype('uint8'))
bm = Bitmap(img)
# Use high alphamax to force curves
paths = bm.trace(alphamax=1.34, opticurve=True)

print(f"Number of curves: {len(paths)}")
curve = paths[0]
print(f"Number of segments in first curve: {len(curve.segments)}")
print(f"Start point: {curve.start_point}")

# Check bezier segment
for seg in curve.segments:
    if not seg.is_corner:
        print(f"\nBezierSegment:")
        print(f"  dir: {[x for x in dir(seg) if not x.startswith('_')]}")
        print(f"  is_corner: {seg.is_corner}")
        print(f"  end_point: {seg.end_point}")
        if hasattr(seg, 'c1'):
            print(f"  c1: {seg.c1}")
        if hasattr(seg, 'c2'):
            print(f"  c2: {seg.c2}")
        break

# Check corner segment
for seg in curve.segments:
    if seg.is_corner:
        print(f"\nCornerSegment:")
        print(f"  dir: {[x for x in dir(seg) if not x.startswith('_')]}")
        print(f"  is_corner: {seg.is_corner}")
        print(f"  end_point: {seg.end_point}")
        print(f"  c: {seg.c}")
        break