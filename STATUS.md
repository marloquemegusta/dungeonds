# STATUS.md - Estado del Proyecto DungeonDS

## Hito 0: Setup de Proyecto y Pipeline Gráfico (Completado)
- [x] Repositorio Git inicializado y estructura de directorios (`source/`, `include/`, `scripts/`, `tools/`, `assets/`, `docs/`).
- [x] Skill `ds-game-dev` y scripts de toolchain automatizados (`scripts/*.ps1`) configurados.
- [x] Documentos de arquitectura y proceso (`AGENTS.md`, `DESIGN.md`, `TECHNICAL.md`, `STATUS.md`).
- [x] Pipeline de pre-renderizado de modelos 3D a spritesheets 8-direccionales (`render_spritesheet.py`) con soporte in-place.
- [x] Banco de pruebas interactivo con escalado nearest-neighbor (`sprite_lab.html`).

## Siguiente Hito (Hito 1): Primer Build NDS y Movimiento de Sprite
- [ ] Scaffold básico de `Makefile` y `main.c` con inicialización de libnds y OAM.
- [ ] Conversión del spritesheet del monstruo/nigromante a formato VRAM NDS (grit).
- [ ] Control del personaje con el D-Pad respondiendo a las 8 direcciones con animación a 60 FPS en el emulador.
