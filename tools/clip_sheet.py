#!/usr/bin/env python3
"""Hoja de contacto ampliada de las capturas de un clip: python tools/clip_sheet.py <nombre> [paso] [columnas] [salida.png]"""
import glob
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
name = sys.argv[1]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 5
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
files = sorted(glob.glob(str(ROOT / "artifacts" / "intro_clips" / name / "c[0-9]_*.png")))[::step]
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (256 * cols, 192 * rows))
for i, f in enumerate(files):
    sheet.paste(Image.open(f).convert("RGB").crop((0, 192, 256, 384)), ((i % cols) * 256, (i // cols) * 192))
out = sys.argv[4] if len(sys.argv) > 4 else str(ROOT / "artifacts" / "intro_clips" / f"{name}_hoja.png")
sheet.save(out)
print(out, len(files))
