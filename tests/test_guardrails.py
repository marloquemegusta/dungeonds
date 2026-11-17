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


WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")


def parse_weapon_table():
    """Lee g_weapon_tuning de weapons.c a {nombre: {campo: int}}."""
    start = WEAPONS_C.index("const WeaponTuning g_weapon_tuning")
    body = WEAPONS_C[start:WEAPONS_C.index("};\n", start)]
    table = {}
    for name, block in re.findall(r"\[(WEAPON_\w+)\]\s*=\s*\{(.*?)\n    \}", body, re.DOTALL):
        table[name] = {k: int(v) for k, v in re.findall(r"\.(\w+)\s*=\s*(-?\d+)", block)}
    return table


def parse_enemy_hp():
    def hp(kind):
        return int(re.search(rf"ENEMY_TYPE_{kind}\] = \{{\s*\.max_hp = (\d+)", GAMEPLAY_C).group(1))
    return {"charger": hp("CHARGER"), "shooter": hp("SHOOTER"), "skeleton": hp("EXVOTO")}


def hits_to_kill(hp, damage):
    return -(-hp // damage)


class BalanceTest(unittest.TestCase):
    """Golpes para matar fijados por DESIGN.md."""

    def test_sniper_hits_to_kill(self):
        hp = parse_enemy_hp()
        sniper = parse_weapon_table()["WEAPON_SNIPER"]
        self.assertEqual(sniper["damage_per_hit"], 150)
        self.assertEqual(hits_to_kill(hp["shooter"], sniper["damage_per_hit"]), 2)
        self.assertEqual(hits_to_kill(hp["charger"], sniper["damage_per_hit"]), 2)
        self.assertEqual(hits_to_kill(hp["skeleton"], sniper["damage_per_hit"]), 1)

    def test_shotgun_hits_to_kill(self):
        hp = parse_enemy_hp()
        shotgun = parse_weapon_table()["WEAPON_SHOTGUN"]
        full_blast = shotgun["damage_per_hit"] * shotgun["pellets"]
        self.assertEqual(shotgun["damage_per_hit"], 40)
        self.assertEqual(hits_to_kill(hp["shooter"], full_blast), 2)
        self.assertEqual(hits_to_kill(hp["charger"], full_blast), 2)
        self.assertEqual(hits_to_kill(hp["skeleton"], full_blast), 1)


if __name__ == "__main__":
    unittest.main()
