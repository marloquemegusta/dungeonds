#!/usr/bin/env python3
import sys
import io
from PIL import Image

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    in_path = sys.argv[1]
    out_path = sys.argv[2]
    max_dim = int(sys.argv[3]) if len(sys.argv) > 3 else 256
    quality = int(sys.argv[4]) if len(sys.argv) > 4 else 85

    img = Image.open(in_path)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')

    w, h = img.size
    if w > max_dim or h > max_dim:
        scale = max_dim / max(w, h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Save as optimized PNG or JPEG
    # If RGBA, save as PNG with optimize=True
    if img.mode == 'RGBA':
        # Check if alpha is fully opaque
        extrema = img.getextrema()
        if extrema and len(extrema) == 4 and extrema[3][0] == 255:
            img = img.convert('RGB')
            img.save(out_path, format='JPEG', quality=quality, optimize=True)
        else:
            img.save(out_path, format='PNG', optimize=True)
    else:
        img.save(out_path, format='JPEG', quality=quality, optimize=True)

if __name__ == '__main__':
    main()
