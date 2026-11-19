"""Normas globales del proyecto (AGENTS.md). Unico sitio de comprobaciones sobre el texto del codigo C."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted((ROOT / "source").glob("*.c")) + sorted((ROOT / "include").glob("*.h"))

# Archivos que pintan efectos visuales (VFX): deben usar paletas apagadas.
VFX_FILES = ["weapons.c", "gems.c", "enemy_laser.c", "groundfx.c", "enemy_ai.c", "grenade.c", "exvoto_melt.c", "boss.c"]

# Excepciones explicitas (archivo, fragmento de la linea). Hoy contienen blanco puro.
VFX_EXCEPTIONS = [
    # Tabla s_fx_rgb heredada de los estilos antiguos de armas; el blanco puro solo vive en ese estilo legacy.
    ("weapons.c", "RGB15(31, 31, 31), RGB15(31, 28, 8)"),
    # Cruz de marca de la granada: blanco puro heredado.
    ("grenade.c", "[K_MARK_CROSS]"),
]


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class FloatGuardTest(unittest.TestCase):
    def test_no_float_or_double_in_source(self):
        # La DS no tiene FPU (AGENTS.md regla 2).
        bad = []
        for path in SOURCES:
            code = re.sub(r'"(?:\\.|[^"\\])*"', '""', strip_comments(path.read_text(encoding="utf-8", errors="replace")))
            for n, line in enumerate(code.splitlines(), 1):
                if re.search(r"\b(float|double)\b", line):
                    bad.append(f"{path.name}:{n}")
        self.assertEqual(bad, [])


class DesaturatedVfxTest(unittest.TestCase):
    def test_vfx_palettes_have_no_pure_primaries_or_white(self):
        bad = []
        for name in VFX_FILES:
            path = ROOT / "source" / name
            for n, line in enumerate(strip_comments(path.read_text(encoding="utf-8")).splitlines(), 1):
                if any(name == f and frag in line for f, frag in VFX_EXCEPTIONS):
                    continue
                for r, g, b in re.findall(r"RGB15\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", line):
                    c = (int(r), int(g), int(b))
                    if c == (31, 31, 31) or (max(c) == 31 and min(c) == 0):
                        bad.append(f"{name}:{n} RGB15{c}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
