# HANDOFF.md - Estado Canónico del Proyecto DungeonDS

**Fecha:** 2026-11-02
**Propósito:** estado mínimo para retomar el trabajo sin depender del chat. Cada tema se detalla en su documento: `AGENTS.md` (reglas), `DESIGN.md` (juego), `TECHNICAL.md` (arquitectura y deuda técnica), `STATUS.md` (historial de sesiones).

---

## 1. Estado del Repositorio

- **Rama base:** `main`. La última entrega integrada es la coherencia de colisión y oclusión con el render del mapa (`walkthroughs/map-export-coherence/walkthrough.md`, registrada en `STATUS.md`).
- **Trabajo en curso:** saneamiento de la deuda de la auditoría `walkthroughs/audit-saneamiento-2d3d/`. La lista pendiente está en `TECHNICAL.md` §4.
- **Build:** BlocksDS en Docker mediante `C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1`.
- **Tests de host:** `tests/`. Fallos conocidos según el walkthrough de coherencia: `test_shadow_masks.py` (faltan assets `e30`) y `test_scenario_state_assertions.py` (import de `run_scenario`).
- **Rendimiento:** objetivo de 60 FPS con `cpu_ticks` ≤ 33514 (AGENTS.md, regla 5). La reconstrucción de oclusión sin índice por fila bajaba a 30 FPS; hoy el runtime busca en binario la primera fila de runs visibles.

## 2. Arquitectura Vigente

- **Mapa:** `isometric_shooter_bl`, 1536×857 px (horneado a 1536×864 con tiles de 8 px), 40,42 px/m. Fuente en `assets/sprites/dungeon/isometric_shooter_bl/`.
- **Pipeline del mapa:** lab Three.js (`tools/lab/export_map_package_headless.cjs`) → `world.png`, `collision.png` y `occlusion_depth.png` → `tools/bake_isometric_shooter_bl.py` → C en `source/` e `include/` → runtime (`source/main.c`). Detalle en `TECHNICAL.md` §3.
- **Oclusión:** profundidad por píxel de la superficie visible, generada en el mismo render que el color. El runtime la compara con la Y de los pies del actor en celdas de 4×4 px.
- **Colisión:** huella sobre el suelo de la geometría en la franja corporal 0,30–1,20 m. Es la única fuente de suelo caminable.
- **Iluminación:** el color del fondo ya incluye la luz del lab (preset cálido en `map_settings.json`). El runtime no tiene iluminación dinámica ni antorcha: `smooth_lightmap.c` se eliminó el 2026-10-21.
- **Niebla de guerra:** no existe en el código.
- **Personajes:** héroe (space marine), charger y necron. Spritesheets de 8 direcciones exportados por el Shader Lab a `assets/sprites/characters/<nombre>/`, convertidos a C por `tools/generate_player_sprites_c.py` en `source/player_sprite.c`.
- **Diseño de juego:** shooter isométrico por salas, descrito en `DESIGN.md` §4. El estado real de cada sistema (enemigos, armas, pickups) está en `TECHNICAL.md` §4.2.

## 3. Reglas Críticas (AGENTS.md)

1. Sin `float` ni `double` en runtime: física y movimiento en punto fijo (`int32_t` con 8.8 o 12.12).
2. Sin comandos interactivos: compilación y emulación con los scripts de la skill `ds-game-dev`.
3. Cada tarea sustancial se desarrolla en un worktree bajo `.worktrees/` (`git worktree add .worktrees/<nombre> -b feat/<nombre>`).
4. Evidencia visual copiada al directorio de artefactos de la sesión y referenciada con su ruta absoluta, sin prefijo `file:///`.
5. Escenarios con geometría verificada: el actor debe cruzar de verdad la entidad que se quiere probar.

## 4. Siguientes Pasos

1. **Deuda prioritaria (`TECHNICAL.md` §4.1):** movimiento y colisión en coordenadas de suelo; escala única entre personaje y mapa (los sprites miden ~0,75 m frente al mapa a 40,42 px/m); anclas de suelo triplicadas.
2. **Resto de la deuda:** gameplay (§4.2), código muerto (§4.3), tests y repo (§4.4).
3. **Plan de juego:** fases A–F de `DESIGN.md` §4.7.
4. **Hardware físico:** subida a la DS sólo con confirmación explícita, mediante la skill `ds-game-dev`.
