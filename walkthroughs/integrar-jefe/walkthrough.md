# Integración de `feat/modo-jefe` en `main` + ROM jugable por defecto

- **Rama / sesión:** `feat/integrar-jefe` -> `main` (2026-11-17)
- **Objetivo:** Integrar el modo jefe (`feat/modo-jefe`: intro con zoom, barra de vida, fases con invulnerabilidad, escolta, victoria con voz y reliquia) con la nueva versión de escenario, IA de enemigos y encuentros de `main`, activando el modo por encuentros en la ROM principal (`dungeonds.nds`) y estructurando el Vía Crucis de 14 stages con el Abanderado en el stage 5 y repetido en los stages 10 y 14 hasta añadir los siguientes jefes.

## Cambios realizados

1. **Integración de `modo-jefe` sobre `main`:**
   - Incorporados `include/boss.h`, `source/boss.c`, `include/sfx_voice_len.h`, `nitrofiles/boss.raw`, `assets/sfx/baked/abanderado_intro.wav`, `assets/sfx/baked/abanderado_derrota.wav`, la lógica de congelado/snapshot/HUD en `source/main.c`, el bloqueo de daño en cambio de fase en `source/gameplay.c`, `enc_start_up_px()` en `source/strip.c`, los hooks en `source/encounters_act1.c` y la documentación en `DESIGN.md` §6.13.7.
   - Mantenido el ajuste de vida del Abanderado de `main` (`ENC_HP_ABANDERADO = 5500` en `include/encounters_act1_hp.h`).
2. **ROM principal jugable por defecto (`templates/blocksds-test/Makefile`):**
   - Activado `-DENCOUNTERS_PROTO=1` por defecto en compilaciones de ROM que no usen `SANDBOX=1`, `BESTIARY_START=1`, `STRESS_TEST=1` ni `GODRAYS_PROTO=1`, manteniendo `include/game.h` en `0` para no romper los tests de host de `strip` y `tide`.
3. **Primer jefe en Stage 5 y jefes repetidos en Stages 10 y 14 (`source/encounters_act1.c`, `source/main.c`):**
   - `ENC_STAGES = 14`: stages 1–4 (encuentros ligeros), **stage 5 (Abanderado)**, stages 6–9 (encuentros medios), **stage 10 (Abanderado repetido)**, stages 11–13 (encuentros duros), **stage 14 (Abanderado repetido -> Victoria)**.
   - Tras vencer al jefe en los stages 5 y 10, `boss_victory()` abre las barreras de la sala, reanuda la música normal, ofrece una Reliquia y permite continuar subiendo al siguiente acto.
   - HUD superior izquierdo actualizado a `ENC x DE 14` / `JEFE x DE 14` y `VICTORIA`.

## Verificación

- **Compilación (`build-project.ps1`):** `dungeonds.nds` (variante `default`) compilada con **0 warnings**.
- **Tests de host (`run-host-tests.ps1`):** `test_strip`, `test_strip_layout_parity`, `test_tide_contract`, `test_guardrails`, `test_cathedral_kit`, `test_navfield`, `test_sniper_hit_volume`, etc. **PASS** (el único fallo es el preexistente `test_bestiary_assets_contract` documentado en `STATUS.md`).
- **Escenario headless (`scenarios/integracion_jefe_stage5.json`):** ejecutado sobre `dungeonds.nds` en DeSmuME: verifica inicio en stage 5 (`current == 4`), intro (`boss_state == 1`), combate (`boss_state == 2`), victoria (`boss_state == 4`) y apertura de barreras hacia stage 6 (`boss_state == 5`, `cleared == 5`, `current == 5`) — **PASS**.
