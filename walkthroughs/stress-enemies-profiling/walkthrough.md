# Profiling de Estrés de Enemigos en Nintendo DS Física

**Fecha:** 2026-11-13  
**Rama temporal de pruebas:** `perf/stress-enemies` (no mergeada a `main`; experimento de diagnóstico)  
**Condiciones de prueba:** enemigos con `1 PS` (`source/horde.c`), jugador invulnerable (`god_mode = 1`), `PERF_PROFILE=1` (salvo la última verificación en `default`).

---

## 1. Resumen ejecutivo

- **Con el sistema actual de sombras suaves** (consulta del color del suelo píxel a píxel + oscurecimiento), subir a **48–72 enemigos** lleva el frame a **34,3–36,5 ms (20 FPS)**. Solo las sombras consumen **15,8 ms (43 % del frame)**.
- **Sin sombras:** la misma horda de 48–72 enemigos baja a **17,3–21,1 ms (30–38 FPS)**, pasándose por apenas 1–4 ms del presupuesto de 16,7 ms (incluyendo ~1,3 ms del propio HUD de perfilado).
- **Con sombras negras alternadas (1 frame sí / 1 no, sin consultar el suelo):**
  - **32 → 40 enemigos:** `14,5–19,5 ms` (**30–56 FPS**).
  - **24 → 26 enemigos:** `12,0–14,1 ms` de media, pero picos de proyectiles (`4–5 ms`) y rebase de franja (`7,6–11,1 ms`) provocan caídas puntuales a **40–50 FPS**.
  - **18 → 20 enemigos:** `8,8–11,7 ms` de media (pico `13,9 ms`), **59–60 FPS constantes** en las 26 ventanas medidas (1.560 frames).
- **Parpadeo en pantalla superior y validación final (`default`, sin log a SD):**
  - Pintando la pantalla superior nada más entrar al VBlank (antes de la lógica del frame siguiente) y quitando la escritura periódica a la SD de `PERF_PROFILE`, el juego con **20 enemigos** y sombras alternadas mantuvo **60 FPS** sin el parpadeo periódico de 1 Hz.
  - **Observación visual:** las sombras negras alternadas a 30 Hz parpadean ligeramente en la pantalla real de la DS; se descarta dejarlas así sin una sesión dedicada de optimización.

---

## 2. Desglose medido en Nintendo DS física

> **Nota sobre calibración de ticks:** con Maxmod/NitroFS activo, el temporizador hardware del perfilador corre con prescaler `/1024` (~`32,7285 ticks/ms`), calibrado contra la duración real de VBlank (`frame_avg = 543 ticks` = `16,6 ms` a 60 FPS; `frame_avg = 1635 ticks` = `50,0 ms` a 20 FPS).

| Escenario | Enemigos | FPS medidos | CPU medio (pico) | Sombras (`sh`) | Sprites (`blit`) | IA (`en`) | Limpieza (`dclr`) | Proyectiles (`proj`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Sombras suaves actuales** | 48 → 72 | **20–21 FPS** | 34,3–36,5 ms (46,8 ms) | **14,4–16,0 ms** | 5,7–6,4 ms | 5,1–5,7 ms | 3,5–4,0 ms | 0,6–3,0 ms |
| **Sin sombras** | 48 → 72 | **30–38 FPS** | 17,3–21,1 ms (26,3 ms) | 0,0 ms | 5,8–8,7 ms | 4,2–5,7 ms | 2,4–4,2 ms | 0,5–2,1 ms |
| **Sombras negras alternadas** | 32 → 40 | **30–56 FPS** | 14,5–19,5 ms (22,4 ms) | 2,5–3,8 ms | 3,6–5,6 ms | 3,7–4,3 ms | 1,4–3,0 ms | 0,4–1,3 ms |
| **Sombras negras alternadas** | 24 → 26 | **40–59 FPS** | 12,0–16,8 ms (26,1 ms) | 1,9–2,6 ms | 2,6–3,5 ms | 2,1–3,1 ms | 1,4–2,8 ms | 0,3–2,6 ms (pico 5,0) |
| **Sombras negras alternadas** | 18 → 20 | **59–60 FPS** | **8,8–11,7 ms (13,9 ms)** | **1,2–2,1 ms** | 1,6–2,9 ms | 1,8–2,9 ms | 1,0–1,9 ms | 0,3–1,5 ms |

---

## 3. Hallazgos técnicos para la futura sesión de optimización

1. **Por qué las sombras cuestan 2,5× más que los sprites (`15,8 ms` vs `6,4 ms`):**
   - `draw_shadow_mask` (`source/main.c`) consulta `world_floor_color(world_x, world_y)` y calcula `apply_shadow_fast(c)` **píxel a píxel** para oscurecer el suelo debajo, además de comprobar oclusión.
   - **Líneas a explorar en la sesión de rendimiento:** sombras tramadas (checkerboard negro sin leer el suelo), sombras por sprites OAM hardware con blending (128 entradas OAM disponibles), o pre-oscurecer / simplificar el óvalo de sombra.
2. **Picos puntuales al combatir y avanzar:**
   - Los proyectiles/láseres añaden picos de `2,6–5,0 ms` en `proj`, y las armas/muertes (`death_chunks`) picos de `3–4 ms` en `wp`.
   - El rebase de la franja mete picos de `7,6–11,2 ms` en `pl`.
3. **Bug detectado en `PERF_PROFILE` con NitroFS (`source/perfprof.c`):**
   - `sfx_init()` llama a `nitroFSInit(NULL)`, que cambia el directorio de trabajo por defecto a `nitro:/` (solo lectura). Al abrir `"/dungeonds_perf.log"` en `perfprof_init()` y `write_window()`, fallaba silenciosamente hasta que se probaron rutas explícitas `fat:/dungeonds_perf.log` y `sd:/dungeonds_perf.log`.
   - Además, la escritura en SD cada 60 frames tarda ~`31 ms` (`sdw_ticks ~ 1030`), lo que provoca un tirón/parpadeo periódico de 1 Hz mientras `PERF_PROFILE=1` está activo.
