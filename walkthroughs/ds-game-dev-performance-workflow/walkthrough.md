# Consolidación de optimización de rendimiento para Nintendo DS

## Lecciones que se vuelven reutilizables

El diagnóstico del suelo FBX mostró por qué una cifra de emulador no basta: DeSmuME registraba unos 5,7 ms para copiar el fondo, mientras que la DSi medía cerca de 38 ms en el contador `F`. Esa diferencia cambió la prioridad: había que eliminar el trabajo de copia por frame y medir el ROM en hardware. La ruta de fondo con tiles y scroll hardware volvió a funcionar bien en la consola; el usuario confirmó que la ROM corregida iba perfecta.

Las copias local y de proyecto de `ds-game-dev` ahora piden una línea base repetible, cronómetros por subsistema con semántica clara, experimentos A/B que cambien una ruta cada vez y validación del mismo input/estado de juego. También documentan que una caché puede acotar la residencia VRAM al viewport aunque atlas y metadata sigan creciendo con el mundo, y que deben forzarse scroll, límites de IDs, primera carga y transferencias en VBlank.

## Alcance de la evidencia

- DSi: confirmación cualitativa del usuario con ROM CRC `65BC36B1`; no hay una lectura numérica nueva del HUD.
- DeSmuME: útil para escenarios y comparaciones repetibles; no predice por sí solo el coste físico de RAM/VRAM.
- Escalabilidad: el generador se estresó con 768×768 y 9.216 tiles; el fixture de 2048×2048 prueba el límite de 65.535 IDs utilizables. Sigue pendiente validar una ROM de mazmorra completa mayor que fuerce vueltas completas del ring en hardware.

## Reproducción

Consultar `Performance optimization workflow` y `Performance profiling and physical hardware` en la skill instalada `%USERPROFILE%/.codex/skills/ds-game-dev/SKILL.md`, y `Performance optimization workflow` en la copia del repositorio. Para el escenario y los límites del generador, ver [pruebas de límites del fondo FBX](../fbx-background-generator-tests/walkthrough.md).