#!/usr/bin/env python3
"""
tests/test_bestiary_assets_contract.py - Contracts for Bestiary font and Exvoto assets.
"""

import os
import sys
import re
import unittest
from PIL import Image

WT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if WT_ROOT not in sys.path:
    sys.path.insert(0, WT_ROOT)

class TestBestiaryAssetsContract(unittest.TestCase):
    def test_files_exist(self):
        expected_files = [
            'include/bestiary_font.h',
            'source/bestiary_font.c',
            'include/bestiary_exvoto.h',
            'source/bestiary_exvoto.c',
            'tools/gen_bestiary_font.py',
            'tools/gen_bestiary_exvoto.py',
            'walkthroughs/bestiario/assets/font_preview.png',
            'walkthroughs/bestiario/assets/exvoto_preview.gif'
        ]
        for rel in expected_files:
            path = os.path.join(WT_ROOT, rel)
            self.assertTrue(os.path.exists(path), f'Missing required file: {rel}')

    def test_no_float_in_c_code(self):
        c_files = [
            'include/bestiary_font.h',
            'source/bestiary_font.c',
            'include/bestiary_exvoto.h',
            'source/bestiary_exvoto.c'
        ]
        float_re = re.compile(r'\b(float|double)\b')
        for rel in c_files:
            path = os.path.join(WT_ROOT, rel)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            m = float_re.search(content)
            self.assertIsNone(m, f'Forbidden float/double keyword found in {rel}: {m}')

    def test_font_preview_dimensions(self):
        preview_path = os.path.join(WT_ROOT, 'walkthroughs', 'bestiario', 'assets', 'font_preview.png')
        with Image.open(preview_path) as im:
            self.assertEqual(im.size, (256, 192), f'Font preview must be exactly 256x192, got {im.size}')

    def test_exvoto_bounds_and_frames(self):
        from tools.gen_bestiary_exvoto import extract_exvoto_strip, DEFAULT_SRC
        bounds, offsets, all_pixels, preview_frames = extract_exvoto_strip(DEFAULT_SRC)
        self.assertEqual(len(bounds), 8)
        self.assertEqual(len(offsets), 8)
        self.assertEqual(len(preview_frames), 8)
        self.assertGreater(len(all_pixels), 2000)
        for f, (x, y, w, h) in enumerate(bounds):
            self.assertGreater(w, 0, f'Frame {f} width should be > 0')
            self.assertGreater(h, 0, f'Frame {f} height should be > 0')
            self.assertLessEqual(x + w, 40)
            self.assertLessEqual(y + h, 40)

    def test_spanish_chars_covered(self):
        from tools.gen_bestiary_font import collect_glyphs, DEFAULT_FONT, DEFAULT_SIZE, DEFAULT_THRESH, SPANISH_CHARS
        font, glyphs, bitmaps = collect_glyphs(DEFAULT_FONT, DEFAULT_SIZE, DEFAULT_THRESH)
        covered_codepoints = {g['codepoint'] for g in glyphs}
        for ch in SPANISH_CHARS:
            self.assertIn(ord(ch), covered_codepoints, f'Spanish char {ch} (0x{ord(ch):04X}) missing from font glyphs')
        for cp in range(0x20, 0x7F):
            self.assertIn(cp, covered_codepoints, f'ASCII char 0x{cp:02X} missing from font glyphs')

if __name__ == '__main__':
    unittest.main()
