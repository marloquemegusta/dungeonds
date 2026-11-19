# Purga de mecánicas y términos obsoletos (`fix/purga-obsoletos`)

- **Fecha:** 2026-11-19
- **Rama:** `fix/purga-obsoletos`

## Qué se ha hecho

1. **Marea (`tide`) y gemas de experiencia (`gems`):**
   - Eliminados `include/tide.h`, `source/tide.c`, `include/gems.h`, `source/gems.c`, `tests/test_tide_contract.py`, `tests/host/tide_host_test.c` y `scenarios/strip_horde_tide.json`, además de su entrada en `.ds-game-dev/project.json`.
   - Retirado el split por VCOUNT de la marea en `source/hwshadow.c` / `include/hwshadow.h`, los parámetros `tide_y` en `horde.c`, `pickups.c` y `godrays.c`, y todas las llamadas en `source/main.c`.
   - Restauradas las curas en el suelo (`include/pickups.h`, `source/pickups.c`, corazones) manteniendo su funcionamiento sin marea.
2. **Escopeta, granada y selector de armas:**
   - Eliminados `include/grenade.h`, `source/grenade.c`, los perdigones (`PlayerProjectile`), los efectos y tabla de escopeta/granada en `source/weapons.c` / `include/weapons.h`, los modificadores de escopeta en `source/modifiers.c` / `include/modifiers.h` y el selector `TEST_WEAPON_CYCLE` en `include/gameplay.h`, `source/gameplay.c` y `source/main.c`.
   - El rayo del Corazón Abierto (`WEAPON_SNIPER`) queda como única arma en todas las variantes (conservando el campo `weapon` en `SandboxMailbox` para no romper escenarios activos).
   - Eliminados `scenarios/enemy_charger_shotgun_stuns_telegraph.json`, `scenarios/sandbox_shotgun_A/B/C.json` y `scenarios/sandbox_grenade_A/B/C.json`.
   - Eliminada la excepción de blanco puro en `tests/test_guardrails.py`.
3. **Marine y Necron:**
   - Eliminados `scenarios/marine_walk_evaluation.json` y `scenarios/necron_walk_evaluation.json`.
   - Actualizadas descripciones y comentarios en código, escenarios activos y `tools/props/contact_sheet.py` (usando `corazon` en lugar de `marine`).
4. **Documentación y referencia de rescate:**
   - Anotado en `DESIGN-ARCHIVE.md` el commit **`7aa3b5f`** como último punto con granada, escopeta, selector de armas, marea y gemas intactos.
   - Actualizados `TECHNICAL.md` (§3.4) y `STATUS.md`. `DESIGN.md`, `LORE.md`, `AGENTS.md` y `assets/MANIFEST.md` sin cambios necesarios.

## Verificación

- **Compilación (`build-project.ps1`):** variantes `default`, `perf`, `cathedral-sandbox`, `godrays` y `stress` — `DS_BUILD=PASS`, **0 avisos**.
- **Tests de host (`run-host-tests.ps1`):** 15/17 PASS (`test_guardrails`, `test_sniper_hit_volume`, `test_strip`, `test_strip_kit`, `test_strip_layout_parity`, `test_upper_screen_contract`, `test_navfield`, `test_cathedral_kit`, `test_cathedral_kit_contract`, `test_blit_runs_contract`, `test_sprite_ground_anchor`, `test_bestiary_contract`, `test_arena_data`, `test_arena_export`, `test_map_export_coherence`); únicamente fallan los 2 tests ya rotos previamente en `main` (`test_bestiary_assets_contract` y `test_character_muzzle`).
