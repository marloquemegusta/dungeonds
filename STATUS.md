# STATUS.md - Estado del Proyecto DungeonDS

## Hito 0: Setup de Proyecto y Pipeline Gráfico (Completado)
- [x] Repositorio Git inicializado y estructura de directorios (`source/`, `include/`, `scripts/`, `tools/`, `assets/`, `docs/`).
- [x] Skill `ds-game-dev` y scripts de toolchain automatizados (`scripts/*.ps1`) configurados.
- [x] Documentos de arquitectura y proceso (`AGENTS.md`, `DESIGN.md`, `TECHNICAL.md`, `STATUS.md`).
- [x] Pipeline de pre-renderizado de modelos 3D a spritesheets 8-direccionales (`tools/render_spritesheet.py`) con soporte in-place verificado sobre el modelo FBX inicial.
- [x] Laboratorio interactivo (`sprite_lab.html`) con escalado nearest-neighbor (1x, 2x, 4x, 8x), filtros de silueta/contraste y previsualización de 8 direcciones.

## Hito 1: Primera Demo Jugable de Mazmorra (Completado)
- [x] Biblioteca de 11 tiles de ruinas góticas horneados desde Dreadhollow 3D (`tools/bake_dungeon_tiles.py`).
- [x] Conversor de tiles y sprites a código C con formato BGR555 (`tools/convert_assets_to_c.py`).
- [x] Motor de juego en C (`source/main.c`) con movimiento 8-direccional en punto fijo 8.8, animaciones fluidas, doble búfer en VRAM y colisiones contra muros/pilares.
- [x] Compilación limpia de la ROM (`dungeonds.nds`) con Docker BlocksDS.
- [x] Verificación de escenario headless en DeSmuME (`scenarios/ruins_exploration.json`) y generación de evidencias visuales.
- [x] Walkthrough documentado en `walkthroughs/01-playable-ruins-prototype/walkthrough.md`.

## Siguiente Hito (Hito 2): Sistema de Niebla / Scroll o Primeras Mecánicas de Nigromancia
- [ ] Cámara con scroll o expansión de mapa procedural.
- [ ] Spawneo de cadáveres o invocación de esbirros esqueletos.
