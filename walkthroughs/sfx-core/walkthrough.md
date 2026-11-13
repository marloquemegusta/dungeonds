# Walkthrough — SFX base del Corazón Abierto (`feat/sfx-core`)

**Fecha:** 2026-11-13  
**Rama:** `feat/sfx-core`

## Qué se ha hecho

1. **Dirección sonora *in-lore* (`DESIGN.md`):**
   - Definidos los 5 SFX base para el Corazón Abierto (fuego sagrado, catedral oscura, hueso y ceniza) sin timbre en `AIM_READY` (silencio limpio al llegar a brazos en cruz).
2. **Pipeline IA + Bake DS:**
   - Configurado `@elevenlabs/cli` (`elevenlabs`) de forma global e incorporadas las reglas de uso en `AGENTS.md` (siempre con `--duration-seconds` mínimo para no gastar créditos extra).
   - Generados y seleccionados por A/B los 5 SFX (`assets/sfx/raw/` → `assets/sfx/baked/` a **16.384 Hz mono, 8-bit**).
   - Creado `tools/bake_sfx.py` para hornear los WAVs a arrays `const int8_t` alineados en `include/sfx_bank.h` y `source/sfx_bank.c` (**23.675 bytes / 23,1 KB** en total).
3. **Mixer hardware y hooks en C (`source/sfx.c`, `include/sfx.h`):**
   - Usa `libnds` (`soundEnable()`, `soundPlaySample()`, `soundKill()`) sin `float`.
   - `heart_charge` (400 ms): se corta de inmediato si se dispara, cancela o muere.
   - `heart_fire` (280 ms): descarga al soltar en `AIM_READY`.
   - `enemy_hit` (95 ms): variación de frecuencia ±12% y cooldown de 2 frames.
   - `enemy_death` (250 ms): combustión súbita con cooldown de 3 frames.
   - `player_hurt` (420 ms): golpe en coraza + quejido de penitente con prioridad máxima.
   - Panning estéreo horizontal (`16..112`) según la posición X respecto a la cámara.

## Verificación

- `build-project.ps1`: `DS_BUILD=PASS`, `0 warnings`, `2.896.384` bytes.
- Tests de host: `test_gameplay_contract.py` (9/9 OK) y `test_weapons_contract.py` (58/58 OK).
- Hardware real (Nintendo DS): ROM subida por FTP (`dungeonds.nds`) y validada por el usuario.

## Qué falta

- Resto del mapa de sonido (según necesidad): granada (lanzamiento + explosión), telegrafías enemigas (láser del Ojo del Tribunal y embestida del Cireneo), impacto en muro, pickups/UI y música (BGM) en fases posteriores.
- Limpieza pendiente de arma única en ROM (retirar escopeta/selección residual cuando toque).
