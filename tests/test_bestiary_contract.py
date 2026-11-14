#!/usr/bin/env python3
"""
tests/test_bestiary_contract.py - Contracts for the Bestiary module.
Verifies DESIGN.md §6.11 presence, no float/double in C runtime code,
no duplication of player_sprite.c assets, existence of all 4 entries,
UTF-8 character coverage in bestiary font, and registration in project.json.
"""

import json
import os
import re
import sys
import unittest

WT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if WT_ROOT not in sys.path:
    sys.path.insert(0, WT_ROOT)

class TestBestiaryContract(unittest.TestCase):
    def test_design_doc_section_present(self):
        design_path = os.path.join(WT_ROOT, 'DESIGN.md')
        self.assertTrue(os.path.exists(design_path), "DESIGN.md must exist")
        with open(design_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('6.11 Bestiario', content, "DESIGN.md must have section 6.11 Bestiario")
        self.assertIn('El Corazón Abierto', content)
        self.assertIn('El Exvoto', content)
        self.assertIn('El Cireneo', content)
        self.assertIn('El Ojo del Tribunal', content)

    def test_files_exist(self):
        expected_files = [
            'include/bestiary.h',
            'source/bestiary.c',
            'include/bestiary_font.h',
            'source/bestiary_font.c',
            'include/bestiary_exvoto.h',
            'source/bestiary_exvoto.c',
            'tools/gen_bestiary_portraits.py',
            'nitrofiles/bestiary/corazon.bin',
            'nitrofiles/bestiary/exvoto.bin',
            'nitrofiles/bestiary/cireneo.bin',
            'nitrofiles/bestiary/ojo.bin',
            'scenarios/bestiary_tour.json'
        ]
        for rel in expected_files:
            path = os.path.join(WT_ROOT, rel)
            self.assertTrue(os.path.exists(path), f"Missing required file: {rel}")

    def test_no_float_or_double_in_c_code(self):
        c_files = [
            'include/bestiary.h',
            'source/bestiary.c',
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
            self.assertIsNone(m, f"Forbidden float/double keyword found in {rel}: {m}")

    def test_no_duplicate_sprites_in_bestiary(self):
        bestiary_c = os.path.join(WT_ROOT, 'source', 'bestiary.c')
        with open(bestiary_c, 'r', encoding='utf-8') as f:
            content = f.read()

        # bestiary.c must reuse sprites via player_sprite.h and bestiary_exvoto.h
        self.assertIn('#include "player_sprite.h"', content)
        self.assertIn('#include "bestiary_exvoto.h"', content)
        self.assertIn('g_player_shot_frames', content)
        self.assertIn('g_charger_telegraph_frames', content)
        self.assertIn('g_charger_charge_frames', content)
        self.assertIn('g_charger_frames', content)
        self.assertIn('g_ojo_look_frames', content)
        self.assertIn('g_ojo_sentence_frames', content)
        self.assertIn('bestiary_exvoto_frames', content)

        # Ensure no giant static bitmap arrays are defined in bestiary.c (e.g. frames arrays with >1000 pixels)
        large_array_re = re.compile(r'uint16_t\s+[a-zA-Z0-9_]+\[\s*\d{4,}\s*\]\s*=')
        m = large_array_re.search(content)
        self.assertIsNone(m, f"bestiary.c must not duplicate large sprite arrays: {m}")

    def test_four_entries_in_bestiary(self):
        bestiary_c = os.path.join(WT_ROOT, 'source', 'bestiary.c')
        with open(bestiary_c, 'r', encoding='utf-8') as f:
            content = f.read()

        required_names = [
            'El Corazón Abierto',
            'El Exvoto',
            'El Cireneo',
            'El Ojo del Tribunal'
        ]
        for name in required_names:
            self.assertIn(name, content, f"Entry name '{name}' missing from bestiary.c")

    def test_utf8_characters_in_font(self):
        from tools.gen_bestiary_font import collect_glyphs, DEFAULT_FONT, DEFAULT_SIZE, DEFAULT_THRESH
        font, glyphs, bitmaps = collect_glyphs(DEFAULT_FONT, DEFAULT_SIZE, DEFAULT_THRESH)
        covered_codepoints = {g['codepoint'] for g in glyphs}

        bestiary_c = os.path.join(WT_ROOT, 'source', 'bestiary.c')
        with open(bestiary_c, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract all string literals from bestiary.c
        str_literals = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', content)
        missing_chars = set()
        for lit in str_literals:
            s = lit.replace(r'\"', '"').replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\\', '\\')
            for ch in s:
                cp = ord(ch)
                if cp in (10, 13):  # newline/return handled by pen
                    continue
                if cp not in covered_codepoints:
                    missing_chars.add((ch, f"0x{cp:04X}"))

        self.assertEqual(len(missing_chars), 0, f"Uncovered UTF-8 characters found: {missing_chars}")

    def test_symbols_and_header_contract(self):
        bestiary_h = os.path.join(WT_ROOT, 'include', 'bestiary.h')
        with open(bestiary_h, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('BestiaryDebugState', content)
        self.assertIn('g_bestiary_debug', content)
        self.assertIn('bestiary_run', content)
        self.assertIn('uint32_t active;', content)
        self.assertIn('uint32_t entry_index;', content)
        self.assertIn('uint32_t frame_count;', content)
        self.assertIn('uint32_t trigger;', content)

    def test_project_json_registered(self):
        pjson_path = os.path.join(WT_ROOT, '.ds-game-dev', 'project.json')
        with open(pjson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        host_tests = data.get('hostTests', [])
        expected_test = "python.exe tests/test_bestiary_contract.py"
        self.assertIn(expected_test, host_tests, f"{expected_test} must be in hostTests")

        variants = data.get('variants', {})
        self.assertIn("bestiary", variants, "variant 'bestiary' must be defined in project.json")
        self.assertIn("BESTIARY_START=1", variants["bestiary"].get("defines", []))

if __name__ == '__main__':
    unittest.main()
