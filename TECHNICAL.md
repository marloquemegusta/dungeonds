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
- **Fuente de verdad visual:** `tools/ds_look.py` define elevación, escala de píxel, cámaras y anclas compartidas por entorno y personaje.
- **Horneado:** `tools/bake_dungeon_iso.py` crea suelo y objetos en cuatro rotaciones; `tools/bake_player.py` crea animaciones en ocho direcciones. Blender es sólo tiempo de edición: no forma parte del runtime.
- **Orientación:** cada segmento de pared/arco/columna usa el sprite horneado para su dirección de mundo. Se hornean las cuatro rotaciones explícitamente.
- **Ancla:** el origen de suelo `(0,0,0)` se proyecta al centro de la celda del canvas. El personaje comparte el ancla de suelo; se planta midiendo la geometría evaluada, no suponiendo que el origen FBX coincide con la suela.
- **Sombras horneadas:** cada orientación de objeto tiene un pase Cycles Shadow Catcher de 128×128; el conversor toma el recorte central 96×96. El jugador tiene una celda 96×96 por dirección, muestreada desde una pose plantada de referencia. El pase se guarda como RGB de luminancia: alfa no codifica cobertura.
- **Máscara:** `tools/shadow_masks.py` estima el nivel iluminado a partir de las esquinas y convierte la reducción de luminancia a cobertura. El conversor debe rechazar pases sin contraste/fondo identificables.
- **Runtime NDS:** cobertura cuantizada a 4 bits (dos píxeles por byte) con límites `[x,y,w,h]`; se oscurece sólo el suelo subyacente válido, nunca `VOID_COLOR`. Orden por frame: suelo → sombras → sprites. No sintetizar elipses/siluetas de sombra por código.
- **Presupuesto:** no guardar máscaras como bytes completos ni usar las dimensiones de horneado completas en C: el primer intento excedía EWRAM. El recorte y empaquetado son parte del contrato de memoria.
- **Verificación:** `python tests/test_shadow_masks.py -v`, conversión del preset, compilación con `scripts/build-project.ps1` y escenario/capturas con `scripts/run-scenario.ps1`. La prueba actual cubre máscaras `e30`; no implica que `e60` se haya regenerado o validado.
