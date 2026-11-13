# Walkthrough — BSO de combate en streaming por NitroFS (`feat/bgm-loop`)

**Fecha:** 2026-11-13  
**Rama:** `feat/bgm-loop`

## Qué se ha hecho

1. **Selección de tema y loops (`assets/music/`):**
   - Extraído **Loop A** (`cathedral_battle_loop.wav`, 12 compases = 21,6 s a 11.025 Hz): pulso tecno industrial + coro grave sin letra en inglés ni drops bruscos, para el bucle continuo de combate.
   - Guardado **Loop B** (`boss_climax_loop.wav`, 16 compases = 28,8 s a 11.025 Hz) como candidato reservado para jefes o fases finales.
2. **Empaquetado NitroFS + Maxmod:**
   - Activado `NITROFSDIR := nitrofiles`, `AUDIODIRS := audio`, `LIBDIRS := $(BLOCKSDS)/libs/maxmod` y `LIBS := -lmm9 -lnds9` en `templates/blocksds-test/Makefile` y `.ds-game-dev/project.json`.
   - `nitrofiles/bgm.raw` (PCM 8-bit con signo, 11.025 Hz, escalado al 42% para dejar margen a los SFX) se lee en streaming con un buffer de 2 KB vía `mmStreamOpen` + `mmStreamUpdate()`.
   - Los 5 SFX pasan al banco de Maxmod (`soundbank.bin` en NitroFS) con `mmEffectEx()` y `mmEffectCancel()`, liberando los 23,1 KB estáticos de `ewram`.

## Verificación

- `build-project.ps1`: `DS_BUILD=PASS`, `0 warnings`, `3.270.656` bytes.
- Tests de host: `test_gameplay_contract.py` (9/9 OK) y `test_weapons_contract.py` (58/58 OK).
- Hardware real (Nintendo DS): ROM subida por FTP y validada por el usuario (música + SFX sin tirones).
