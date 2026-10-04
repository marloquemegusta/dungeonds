# TECHNICAL.md - Especificación Técnica y Arquitectura

## 1. Plataforma y Toolchain
- **CPU:** ARM946E-S @ 67 MHz (Nintendo DS principal) + ARM7TDMI @ 33 MHz (audio/input).
- **FPU:** No existe por hardware. Todo cálculo trigonométrico o posicional usa punto fijo entero `fixed32` (8.8 o 12.12).
- **Toolchain:** BlocksDS (`skylyrac/blocksds:slim-latest`) + libnds v2 compilado mediante Docker (`scripts/build-project.ps1`).
- **Emulación headless:** DeSmuME headless en entorno WSL2 para validación determinista por escenarios (`scripts/run-scenario.ps1`).

## 2. Presupuestos y Arquitectura de Memoria
- **RAM Principal:** 4 MB compartidos entre código, datos de nivel, entidades y audio.
- **VRAM 2D:**
  - Fondos de mazmorra en Tilesets BG 8x8 con paleta indexada (16 o 256 colores).
  - Entidades dinámicas (jugador, esbirros, enemigos, proyectiles) alojadas en los 128 slots del motor OAM de sprites 2D.
- **Framerate Objetivo:** 60 FPS estables.

## 3. Pipeline de Assets
- Modelos 3D animados (.fbx / .gltf) $\to$ `render_spritesheet.py` (Blender headless, 8 direcciones, in-place lock) $\to$ Spritesheets PNG $\to$ Conversión a C / binarios NDS vía `grit`.
