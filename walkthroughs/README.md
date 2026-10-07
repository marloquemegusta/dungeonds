# Walkthroughs por Sesión

Resúmenes acumulativos y auditables de cada entrega y avance de desarrollo en `dungeonds`.

## Convención

- Una carpeta por hito o sesión atómica: `walkthroughs/<nombre-sesion>/`.
- Dentro, el resumen `walkthrough.md` y sus evidencias visuales (GIFs, capturas) en `walkthroughs/<nombre-sesion>/assets/`.
- Los assets se enlazan con rutas relativas al propio `.md` (por ejemplo `assets/foo.png` o `assets/foo.gif`).
- Estos archivos se versionan en Git para mantener el historial vivo de evolución del proyecto.

## Índice de sesiones

| # | Hito / Sesión | Carpeta | Estado |
| :---: | :--- | :--- | :--- |
| 0 | Setup de proyecto, pipeline 3D a 2D y catálogo de ruinas | [`00-project-setup-pipeline/`](00-project-setup-pipeline/walkthrough.md) | Completado |
| 1 | Primera demo interactiva: Ruinas y movimiento 8-dir en NDS | [`01-playable-ruins-prototype/`](01-playable-ruins-prototype/walkthrough.md) | En progreso |
| 2 | Motor de renderizado dimétrico, look compartido y presets e30/e60 | [`02-isometric-renderer/`](02-isometric-renderer/walkthrough.md) | Completado |
| 3 | Iluminación de mazmorra gótica y outline de legibilidad | [`03-dungeon-atmosphere-and-outline/`](03-dungeon-atmosphere-and-outline/walkthrough.md) | Completado |
| 4 | Enemigo cargador (Run.fbx) y cambio dinámico de personaje | [`04-enemy-charger-and-character-swap/`](04-enemy-charger-and-character-swap/walkthrough.md) | Completado |
| 5 | Arquitectura de rendimiento a 60 FPS y corrección de alineamiento ARM9 | [`05-arm9-alignment-and-60fps/`](05-arm9-alignment-and-60fps/walkthrough.md) | Completado |
| 6 | Corrección de colisión y profundidad (depth sorting) en pilares | [`06-pillar-collision-and-depth-alignment/`](06-pillar-collision-and-depth-alignment/walkthrough.md) | Completado |
| 7 | Integración de enemigo esqueleto (skeleton.fbx) y reorganización de assets | [`07-skeleton-enemy-and-asset-cleanup/`](07-skeleton-enemy-and-asset-cleanup/walkthrough.md) | Completado |
| 8 | Estandarización del pipeline de shaders, normales y contraste de personajes | [`08-standardize-character-shaders/`](08-standardize-character-shaders/walkthrough.md) | Completado |
| 9 | Rendimiento 60 FPS Dual-Screen, Corrección Diagonal y Multi-Entidad (10 Enemigos) | [`09-dual-screen-60fps-and-multi-entity/`](09-dual-screen-60fps-and-multi-entity/walkthrough.md) | Completado |
| 10 | Hardware Background Scrolling a 60 FPS en Dual-Screen | [`10-hardware-bg-scroll-60fps/`](10-hardware-bg-scroll-60fps/walkthrough.md) | Completado |
| 11 | Mejora de Rendimiento y Pipeline: Background Scroll Streaming, Stutter y Alineación de Pilares | [`11-perf-bg-scroll-and-rendering/`](11-perf-bg-scroll-and-rendering/walkthrough.md) | Completado |
| 12 | Prototipo de combate: Lanza ósea (A y lápiz táctil) | [12-bone-lance-prototype](12-bone-lance-prototype/walkthrough.md) | Validado en emulador |
| 13 | Escopeta de perdigones de hueso (5 astillas, <1 m) | [13-bone-shotgun-pellets](13-bone-shotgun-pellets/walkthrough.md) | Validado en emulador |
| 14 | Lanza ósea procedural (astillas sin outline y motas espectrales) | [14-bone-particle-lance](14-bone-particle-lance/walkthrough.md) | Prototipo GIF validado en emulador |
| 15 | Lanza más rápida sin azul y fragmentación al morir | [15-bone-projectile-revision](15-bone-projectile-revision/walkthrough.md) | Validado en DeSmuME |

