import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SANDBOX_H = (ROOT / "include" / "sandbox.h").read_text(encoding="utf-8")
SANDBOX_C = (ROOT / "source" / "sandbox.c").read_text(encoding="utf-8")
ENEMY_AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
PROJECT = json.loads((ROOT / ".ds-game-dev" / "project.json").read_text(encoding="utf-8"))

# Mailbox layout contract: (offset, field name, C declaration in sandbox.h).
MAILBOX_LAYOUT = [
    (0, "seq", "uint32_t seq;"),
    (4, "ack", "uint32_t ack;"),
    (8, "player_x", "int16_t player_x;"),
    (10, "player_y", "int16_t player_y;"),
    (12, "weapon", "uint8_t weapon;"),
    (13, "style", "uint8_t style;"),
    (14, "enemy_count", "uint8_t enemy_count;"),
    (15, "flags", "uint8_t flags;"),
    (16, "enemies", "SandboxEnemy enemies[SANDBOX_MAX_ENEMIES];"),
]


class SandboxHeaderTest(unittest.TestCase):
    def test_layout_comment_documents_every_offset(self):
        layout_comment = "\n".join(line for line in SANDBOX_H.splitlines() if line.startswith("//"))
        for offset, name, _ in MAILBOX_LAYOUT:
            self.assertRegex(layout_comment, rf"\b{offset} {name}\b", f"{name} @ {offset}")

    def test_struct_declares_fields_in_contract_order(self):
        mailbox = SANDBOX_H[SANDBOX_H.index("typedef struct {\n    uint32_t seq;"):]
        positions = []
        for _, _, declaration in MAILBOX_LAYOUT:
            self.assertIn(declaration, mailbox)
            positions.append(mailbox.index(declaration))
        self.assertEqual(positions, sorted(positions))

    def test_enemy_entry_is_six_bytes(self):
        body = SANDBOX_H[SANDBOX_H.index("typedef struct {\n    uint8_t type;"):]
        for declaration in ("uint8_t type;", "uint8_t flags;", "int16_t x;", "int16_t y;"):
            self.assertIn(declaration, body)

    def test_sandbox_is_off_by_default(self):
        self.assertIn("#define SANDBOX 0", SANDBOX_H)


class SandboxSourceTest(unittest.TestCase):
    def test_layout_is_asserted_at_compile_time(self):
        for offset, name, _ in MAILBOX_LAYOUT:
            self.assertRegex(
                SANDBOX_C,
                rf"_Static_assert\(offsetof\(SandboxMailbox, {name}\) == {offset}\b",
                name,
            )
        self.assertIn("_Static_assert(sizeof(SandboxEnemy) == 6", SANDBOX_C)
        self.assertIn("_Static_assert(sizeof(SandboxMailbox) == 112", SANDBOX_C)

    def test_all_content_lives_under_sandbox_guard(self):
        guard = SANDBOX_C.index("#if SANDBOX\n")
        end = SANDBOX_C.rindex("#endif")
        head = SANDBOX_C[:guard]
        body = SANDBOX_C[guard:end]
        for symbol in ("SandboxMailbox g_sandbox;", "int g_sandbox_freeze_ai;", "void sandbox_update(",
                       "_Static_assert(", "static void sandbox_clear(", "static void sandbox_spawn("):
            self.assertNotIn(symbol, head, symbol)
            self.assertIn(symbol, body, symbol)
        self.assertIn("typedef int sandbox_translation_unit_not_empty;", head)

    def test_spawn_never_touches_enemies_total(self):
        spawn = SANDBOX_C[SANDBOX_C.index("static void sandbox_spawn("):SANDBOX_C.index("void sandbox_update(")]
        self.assertNotIn("enemies_total", spawn)

    def test_sandbox_packs_are_marked_awake(self):
        self.assertIn("pack_awake[MAX_PACKS - 1] = 1", SANDBOX_C)


class SandboxIntegrationTest(unittest.TestCase):
    def test_main_applies_request_before_player_update(self):
        sandbox_call = MAIN_C.index("sandbox_update(")
        player_call = re.search(r"(?<!void )player_update\(", MAIN_C)
        self.assertIsNotNone(player_call)
        self.assertLess(sandbox_call, player_call.start())

    def test_enemy_ai_honours_freeze_after_stun_block(self):
        self.assertIn('#include "sandbox.h"', ENEMY_AI_C)
        self.assertIn("g_sandbox_freeze_ai", ENEMY_AI_C)
        stun = ENEMY_AI_C.index("e->stun_timer > 0")
        freeze = ENEMY_AI_C.index("if (g_sandbox_freeze_ai) continue;")
        dormant = ENEMY_AI_C.index("ENEMY_STATE_DORMANT) continue;")
        self.assertLess(stun, freeze)
        self.assertLess(freeze, dormant)

    def test_sandbox_reads_the_aura_look_from_flag_bits_3_4(self):
        self.assertIn("#define SANDBOX_FLAG_AURA_SHIFT 3", SANDBOX_H)
        self.assertIn("g_fx_style = g_sandbox.style % FX_STYLE_COUNT;", SANDBOX_C)
        self.assertIn("g_aura_style = ((flags & SANDBOX_FLAG_AURA_MASK) >> SANDBOX_FLAG_AURA_SHIFT) % AURA_STYLE_COUNT;",
                      SANDBOX_C)

    def test_project_declares_sandbox_variant(self):
        self.assertIn("SANDBOX=1", PROJECT["variants"]["sandbox"]["defines"])


if __name__ == "__main__":
    unittest.main()
