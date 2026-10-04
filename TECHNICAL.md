# TECHNICAL.md - Especificación Técnica y Arquitectura

## 1. Plataforma y Toolchain NDS
- **Consola:** Nintendo DS (ARM946E-S @ 67 MHz para lógica/render, ARM7TDMI @ 33 MHz para audio/input).
- **Aritmética:** Sin FPU hardware. Todo cálculo físico o posicional se realiza en punto fijo entero (`int32_t`, 8.8 o 12.12).
- **Toolchain:** BlocksDS (`skylyrac/blocksds:slim-latest`) vía Docker (`scripts/build-project.ps1`).
- **Emulación determinista:** DeSmuME headless sobre WSL2 (`scripts/run-scenario.ps1`).

## 2. Presupuestos Hardware de Nintendo DS
- **RAM Principal:** 4 MB.
- **Hardware 2D (OAM):** 128 entradas máximas de sprites por hardware.
- **Resolución nativa:** 256×192 píxeles por pantalla.

## 3. Pipeline de Assets
- **Herramienta:** `tools/render_spritesheet.py` (Blender headless).
- **Entrada:** Modelos 3D (.fbx, .gltf, .obj) con animaciones esqueléticas.
- **Salida:** Spritesheets 8-direccionales con eliminación automática de traslación (*in-place*) y canal alfa.
