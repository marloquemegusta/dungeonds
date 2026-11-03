# Auditoría del motor 2D/3D y prototipo A (2026-11-03)

Rama de medida: `audit/motor-2d3d` (antes) y `proto/compositor-a` (prototipo A). Cambios de código solo en A; esta sesión documenta el resultado.

## 0. Diagnóstico en una frase

El motor no está podrido de base: el coste estaba concentrado en trabajo fijo de pantalla completa (limpiar y copiar un framebuffer de 96 KB y reconstruir un mapa de oclusión en cada movimiento de cámara), no en dibujar actores.

## 1. Método

- ROM de perfilado (`PERF_PROFILE`, `include/perfprof.h`): una línea por ventana de 60 frames en `/dungeonds_perf.log` de la SD. Nota: libnds FAT solo guarda el tamaño del fichero al hacer `fclose`.
- Revisiones por área con subagentes (render, assets, pipeline, gameplay, tests).
- Medidas en DS real, no en DeSmuME (que penaliza VRAM y no modela EWRAM/caché).

## 2. Medidas en DS real (ms/frame, media / máx)

Antes = `audit/motor-2d3d`, 1500 frames. A = `proto/compositor-a`, 2520 frames.

| Concepto | Antes | A |
| :--- | :--- | :--- |
| Mapa de oclusión (`occ`) | 3,88 / 7,50 | 0 / 0 |
| Limpieza (`clr` → `dclr`) | 5,48 / 11,00 | 0,22 / 1,26 |
| Copia de página (`pcopy`) | 1,78 / 1,83 | 0 / 0 |
| HUD | 1,60 / 1,69 | 0,31 / 1,47 (solo con START) |
| Sombras | 0,41 / 2,10 | 0,41 / 3,04 |
| Blit de actores | 0,25 / 1,10 | 0,27 / 2,08 |
| Base de pared | 0,02 / 0,14 | 0,04 / 0,42 |
| Anillo BG inferior | 0,15 / 2,15 | 0,12 / 2,18 |
| Anillo BG superior | 0,13 / 1,98 | 0,12 / 1,78 |
| **CPU total** | **12,03 / 15,56** | **1,58 / 3,98** |
| **Frame** | **18,93 / 35,85** | **16,54 / 19,46** |

- Frames con más de un vblank: 226/1500 → 12/2520 (≈ los frames de escritura a SD, ~39 ms una vez por ventana).
- Frames con transparencia activa: 375 → 1039.

## 3. Hallazgos

### FUNDACIONAL
- **Compositor por software a pantalla completa (clear 96 KB + DMA 96 KB).** RESUELTO en A: dibujo directo en la página trasera de VRAM y limpieza por spans sucios (`game.h` `DirtySpan`/`dirty_row`/`dirty_rect`, `main.c` `clear_dirty_spans`), con modo `DIRTY_VERIFY` de comprobación (`dirty_leaks`, offset 64 en `g_perf`).
- **Timestep por frame presentado.** PENDIENTE: a 30 FPS todo va a media velocidad; con A el juego va a 60 pero no hay tolerancia.
- **Transparencia por parpadeo temporal (`s_frame_index & 1`).** PENDIENTE: solo funciona a 60 FPS estables; la base de pared depende de ella y sale de la rejilla de colisión. Rediseño propuesto: patrón espacial estable o alfa por hardware (con OAM: OBJ semitransparente/ventanas; con 3D: Z-buffer + translucidez).

### RENDIMIENTO
- **Reconstrucción del mapa de oclusión 4×4 por movimiento de cámara.** RESUELTO en A: consulta directa a `g_dungeon_occlusion_runs` por fila (`find_first_occlusion_run_in_row`, `find_hiding_run`, `occlusion_blocks_pixel` con búsqueda binaria); exacta al píxel.
- **HUD siempre activo con 4 `snprintf`; logs `snprintf`+`nocashMessage` en eventos calientes.** RESUELTO en A: HUD con START, logs tras `#ifdef DEBUG`. Nota: el Makefile no define `DEBUG` y `encounters.c` conserva 3 `nocashMessage`.
- **Anillo de BG reescanea 2048 celdas por pantalla en cada cambio de tile.** PENDIENTE (baja prioridad): en hardware ~0,1 ms de media, picos ~2 ms.
- **Assets.** PENDIENTE: sprites BGR555 crudos (614 KB) + máscaras de sombra 4 bpp 80×80 (614 KB), sin paleta, compresión ni NitroFS; binario ~2,0 MiB de 3,5 MiB de EWRAM del linker; ITCM/DTCM sin uso del juego.

### CONVENCIÓN
- **Métricas engañosas.** `cpu_percent` excluía DMA y anillo BG; la regla 5 de `AGENTS.md` usaba 33514 (= 1 ms) como umbral de 30 FPS cuando el presupuesto es 560190 ticks; comentario obsoleto en `game.h` (280095). Regla 5 corregida en esta sesión (vblanks>1 / fps<60 o `cpu_ticks` frente a 560190, medido en hardware con `PERF_PROFILE`). Comentario de `game.h`: PENDIENTE (código).
- **Acoplamiento.** PENDIENTE: coordenadas de mundo = píxeles de pantalla; impactos con círculo en pantalla vs movimiento con métrica de suelo; estado global en `main.c`; lógica que copia píxeles (`on_enemy_death`).
- **Escenario de DeSmuME sensible a frames perdidos** (pasa/falla según HUD o carga) y DeSmuME no representativo del coste de hardware. PENDIENTE: los escenarios deberían basarse en frames de lógica, no en vblanks; el rendimiento solo se valida en DS.

### HIGIENE
- **Pipeline.** PENDIENTE: `tools/rebuild-assets.ps1` llama a `tools/build_assets.py` inexistente; `generate_player_sprites_c.py` copia texto del `.h` del lab en vez de convertir `shadow.png`; tamaño del mundo en 4 sitios; `SPAWN` hardcodeado en el baker; `.c` generados versionados sin hash de origen; ~40 scripts muertos en `tools/`.

## 4. Decisión

A es suficiente para rendimiento (CPU 1,6 ms de media sobre 16,7). B (OAM) y C (motor 3D) quedan descartados por rendimiento; solo se reconsiderarían para resolver transparencias/convención. Siguiente paso recomendado: rediseñar transparencias sobre A.

## 5. Limitaciones

- La comparación de imagen píxel a píxel solo es concluyente en el spawn (las otras capturas desfasan frames).
- La oclusión nueva no oculta los píxeles de más que ocultaban las celdas 4×4 (cambio esperado).
- Validación visual en la DS pendiente de confirmación del usuario.
