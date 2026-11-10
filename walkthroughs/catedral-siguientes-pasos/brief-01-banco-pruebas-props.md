# Brief 01 · Banco de pruebas de props (Luna)

**Rama sugerida:** `feat/props-showcase` · **Modelo:** `luna` · **Coordinador:** compila, ejecuta y revisa capturas.

## Objetivo

Crear la variante de build `props-showcase`, que coloca los seis props físicos (columna, santo, relicario, vela, banco_roto, banco_volcado) en posiciones **fijas y conocidas**, sin el resto del atrezo. Con ella, un escenario empuja al marine contra cada prop por el norte, el sur, el este y el oeste, y comprueba que se detiene. Las capturas permiten revisar la oclusión: detrás oculto, delante visible.

## Contexto que necesitas

- `source/strip.c`: `stamp_band()` coloca estampas en una banda con tres pasos: copia los tiles al mapa, escribe la huella en `s_collision` (runs de `StripFootprintRun`) y añade runs de oclusión (`StripDepthRun`, profundidad = Y de mundo de la estampa + `foot_anchor_y_px` + `depth_delta`). Después de colocar, `rebuild_occlusion_index()` ordena los runs.
- El patrón de depuración ya existe: `#if LAPIDA_DEBUG` → `strip_debug_lapidas()` pinta lápidas en posiciones fijas, pero **solo los tiles**. Tu versión tiene que hacer los tres pasos.
- Orden de estampas en `source/strip_kit.c` (`s_stamps`): índices 0–3 banco_roto, 4–7 banco_volcado, 8–11 columna, 12–15 relicario, 16–19 santo y 20–23 vela (cuatro fases de suelo cada uno), y de 24 en adelante las lápidas. Comprueba el orden en el archivo antes de usarlo.
- Ventana: 512×2048 px. El jugador empieza en y=1792. **Si el jugador queda por debajo de y=768, se hace un rebase y todo baja 512 px.** Coloca los props entre y=1000 y y=1700, para que ningún poke cause rebase.
- Suelo transitable entre x=48 y x=464. Coordenadas de tile: x_tile entre 6 y 57 menos el ancho de la estampa. Las coordenadas Y de tile deben respetar la fase de la estampa (`phase_row`, `phase_col`), igual que en `stamp_band()`.
- Escenarios: mira `scenarios/cathedral_bench_collision.json`, con los mismos campos `state`, `poke`, `button_down` y `state_capture`. El buzón está en `include/sandbox.h`. Para que los muñecos del playground no estorben, usa el flag de limpiar enemigos (`SANDBOX_FLAG_CLEAR`) en el primer poke.

## Pasos

1. Extrae de `stamp_band()` una función `static void stamp_place(const StripStamp *s, int x_tile, int y_tile, int map_row, int collision_row)` que haga los tres pasos, y úsala en `stamp_band()`. El comportamiento no debe cambiar.
2. Con `#if PROPS_SHOWCASE`: en `strip_start()`, genera las bandas sin estampas aleatorias (solo suelo) y coloca un ejemplar de cada prop físico con `stamp_place()` en una rejilla fija de 3×2. Deja al menos 48 px libres entre piezas. Llama a `rebuild_occlusion_index()`. Si el jugador hace rebase, `strip_rebase_if_needed()` genera bandas nuevas arriba; no hace falta poner props ahí.
3. Añade la variante a `.ds-game-dev/project.json`: `"props-showcase": {"defines": ["SANDBOX=1","PLAYGROUND=1","CATHEDRAL_PLAYGROUND=1","PROPS_SHOWCASE=1"]}`.
4. Escribe en el brief de entrega una **tabla de geometría**: para cada prop, la esquina superior izquierda en mundo, la caja de su huella en mundo (de sus `foot_runs`: x0, x1, y0, y1) y los cuatro puntos de partida del escenario. Cada punto de partida queda 24 px fuera de la huella, alineado con el centro de su lado.
5. Escribe `scenarios/props_showcase_contacts.json`. Para cada prop y cada dirección: poke del jugador en el punto de partida, mantener la dirección hacia el prop 90 frames, capturar estado y pantalla, otros 30 frames y capturar de nuevo. Asertos: que entre las dos capturas la posición no cambie (`max_abs_delta` 2000 en la coordenada de avance) y que, desde el punto de partida, no avance más de 24 px (`max_abs_delta` 6144 en 8.8). La ruta del ELF es `../.ds-game-dev/build/out/dungeonds-props-showcase.elf`. Nombres de captura veraces: `columna_n_held`, `columna_s_held`, etc. (`AGENTS.md`, regla 5).
6. Añade un test de host con contrato de texto en `tests/test_props_showcase_contract.py`: comprueba que `stamp_place` existe, que `stamp_band` la usa y que `PROPS_SHOWCASE` no aparece fuera de `#if`. Declara el test en `hostTests`.

## Restricciones

- No cambies la distribución normal ni el baker. No toques `strip_kit.c`.
- La build por defecto y `cathedral-playground` deben generar exactamente el mismo mapa que antes. El paso 1 es solo una refactorización.

## Criterio de aceptación (lo comprueba el coordinador)

- `build-project.ps1 -Variant props-showcase` y `-Variant cathedral-playground-perf` con 0 warnings nuevos.
- `run-host-tests.ps1` PASS.
- `cathedral_props_depth_collision` y `cathedral_bench_collision` siguen en PASS (la refactorización no cambia nada).
- `props_showcase_contacts` en PASS. En las capturas, el marine está tocando el prop correcto en las 24 posiciones: detrás queda oculto por el prop y delante se ve entero. Si una captura no muestra el contacto, la geometría está mal y se corrige antes de dar nada por bueno.
- Hoja de contacto 4× NEAREST de las 24 posiciones en `walkthroughs/props-showcase/assets/`.

## Comandos del coordinador

```powershell
$p='<ruta del worktree>'; $sk='C:\codexlocal\skills\agentic-ds-dev\scripts'
& "$sk\build-project.ps1" -ProjectPath $p -Variant props-showcase
& "$sk\run-host-tests.ps1" -ProjectPath $p
& "$sk\run-scenario.ps1" -ProjectPath $p -ScenarioPath "$p\scenarios\props_showcase_contacts.json" -RomPath "$p\dungeonds-props-showcase.nds"
```
