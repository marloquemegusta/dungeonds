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
| 16 | DS Shader Lab interactivo, selector de FBX y tamaño de sprite en píxeles | [`16-shader-lab-interactive/`](16-shader-lab-interactive/walkthrough.md) | Completado |
| 17 | Shader Lab importa FBX sin buscar sidecars .fbm | [`17-shader-fbx-image-search/`](17-shader-fbx-image-search/walkthrough.md) | Verificado con Blender |
| 18 | Diagnóstico de la carga y render lento de Mario en Shader Lab | [`18-profile-mario-vs-hero/`](18-profile-mario-vs-hero/walkthrough.md) | Medido en servidor y Blender |
| 19 | Integración Modular del Dungeon 3D (FBX) en el Motor Nintendo DS | [`19-modular-3d-scifi-dungeon/`](19-modular-3d-scifi-dungeon/walkthrough.md) | Validado en DeSmuME (GIF) |
| 23 | Reparación de puntos de colisión FBX y recorte de spans de oclusión | [`fbx-collision-perf-followup/`](fbx-collision-perf-followup/walkthrough.md) | ROM subida; validación física pendiente |
| 24 | Diagnóstico A/B de la regresión de rendimiento FBX | [`full3d-performance-gap/`](full3d-performance-gap/walkthrough.md) | Medido en DeSmuME; optimización arquitectónica pendiente |
| 25 | HUD FPS y diagnóstico de rendimiento en Nintendo DSi | [`fps-hud/`](fps-hud/walkthrough.md) | Fix ARM9 comprometido; carga FTP fallida; prueba DSi pendiente |
| 26 | Perfilado de tres rutas para el suelo FBX | [`fbx-floor-render-options/`](fbx-floor-render-options/walkthrough.md) | Ring y generador 768×768 validados; ROM subida; HUD DSi pendiente |


- [Reparación de navegación de la mazmorra FBX](fbx-navigation-repair/walkthrough.md) — conversión y colisión para la escena FBX; incluye escenarios con estado real y límites de validación.
- [Experimento de oclusión para la mazmorra FBX](fbx-occlusion-experiment/walkthrough.md) — prototipo de spans de profundidad; la verificación de máscara y el presupuesto de rendimiento siguen fallando.

- [FBX collision grid and wall-stop check](fbx-collision-fix/walkthrough.md) — host tests and state-backed DeSmuME wall-stop scenario pass; doorway connectivity remains unverified.
