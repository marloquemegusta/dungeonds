"""Normas globales del proyecto (AGENTS.md). Unico sitio de comprobaciones sobre el texto del codigo C."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted((ROOT / "source").glob("*.c")) + sorted((ROOT / "include").glob("*.h"))

# Archivos que pintan efectos visuales (VFX): deben usar paletas apagadas.
VFX_FILES = ["weapons.c", "glifo.c", "enemy_laser.c", "groundfx.c", "enemy_ai.c", "exvoto_melt.c", "boss.c", "campanero_fx.c", "pickups.c"]

# Excepciones explicitas (archivo, fragmento de la linea).
VFX_EXCEPTIONS = []


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


# Clips que viven residentes en player_sprite.c (heroe y sus variantes). Cualquier otro clip con arrays grandes ahi
# es un enemigo que se ha colado: va a nitrofiles/chars/ y a un grupo de chars_pool.c.
HERO_RESIDENT_CLIPS = {"player", "hero_crouch_walk", "player_shot"}


class ResidentArtTest(unittest.TestCase):
    def test_player_sprite_c_only_holds_hero_clips(self):
        # Arrays grandes (frames, runs, shadow_masks) definidos con `[]` e inicializador; los de los clips de pool son
        # punteros NULL, y los stubs de un solo elemento (`{ 0 }`) no ocupan nada.
        text = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8", errors="replace")
        pat = re.compile(r"^const (?:uint16_t|uint8_t) g_(\w+?)_(?:frames|runs|shadow_masks)\[\][^=]*=\s*\{(.*?)\};", re.M | re.S)
        bad = sorted({m.group(1) for m in pat.finditer(text)
                      if m.group(2).strip().rstrip(",").strip() != "0" and m.group(1) not in HERO_RESIDENT_CLIPS})
        self.assertEqual(bad, [], f"clips de enemigo con arrays grandes en player_sprite.c: {bad}. Van a nitrofiles/chars/ y a "
                                  "un grupo de chars_pool.c (STREAMED en tools/generate_player_sprites_c.py), no a la ROM; "
                                  "el heroe se anade a HERO_RESIDENT_CLIPS solo si es suyo.")


class ShadowMaskFormatTest(unittest.TestCase):
    def test_remate_bins_have_one_bit_masks(self):
        # 'RMT1' = mascaras de sombra a 1 bpp; 'RMAT' era la de 4 bpp. Los bins se migran con
        # tools/generate_remate_sprites.py --migrate-masks y los empaquetadores escriben ya 'RMT1'.
        bins = sorted((ROOT / "nitrofiles" / "remate").glob("*.bin"))
        self.assertTrue(bins)
        bad = [p.name for p in bins if p.read_bytes()[:4] != b"RMT1"]
        self.assertEqual(bad, [], "bins de remate con mascara de 4 bpp (o sin cabecera valida): migrar a RMT1")

    def test_character_and_boss_bins_have_valid_headers(self):
        # CHR1 y CAMP no llevan campo de formato de mascara: aqui solo se comprueba que su cabecera es la vigente
        # (un bin viejo o ajeno se detecta). Las mascaras de estos bins son 1 bpp por construccion del generador.
        bad = [p.name for p in sorted((ROOT / "nitrofiles" / "chars").glob("*.bin")) if p.read_bytes()[:4] != b"CHR1"]
        bad += [p.name for p in sorted((ROOT / "nitrofiles" / "campanero").glob("*.bin")) if p.read_bytes()[:4] != b"CAMP"]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
