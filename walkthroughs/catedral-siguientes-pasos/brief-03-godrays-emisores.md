# Brief 03 · Emisores de godrays: lancetas laterales y rosetón frontal (Luna)

**Rama sugerida:** `feat/godrays-emisores` · **Modelo:** `luna` · Independiente de los briefs 01 y 02.

## Objetivo

Cada haz de luz sale de la ventana que lo emite:

- **Lancetas** en los muros laterales, alternando lado cada 256 px. Usan las variantes de lanceta.
- **Rosetón** frontal en el arco del crucero, centrado en x=256 y una vez por ciclo de 1.024 px. Usa la variante de rosetón.
- **Prioridad:** en la pantalla donde se ve el rosetón no se dibuja ningún haz lateral. La ventana lateral sigue visible en el muro, pero sin haz. Decisión escrita en `DESIGN.md` §6.9.1b, sesiones 2 y 3.

## Contexto que necesitas

- `source/godrays.c`, `render_screen()`:
  - el periodo es `GODRAY_PERIOD=256`, con ancla `GODRAY_ANCHOR=64`;
  - la Y absoluta es `camera_y + strip_shift_total_px()`;
  - la variante del haz sale de `period % GODRAY_RAY_COUNT`, y por eso hoy el rosetón cae a veces en un muro lateral;
  - el lado sale de `period & 1`.
- Gráficos en `source/godrays_gfx.c` e `include/godrays_gfx.h` (`GODRAY_RAY_COUNT`, `g_godray_ranges`). Comprueba qué índice es cada variante; los PNG de origen están en `assets/sprites/godrays/` y las notas en `tools/godrays/README.md`. **Si no hay variante de rosetón en los gráficos compilados, para y avisa: regenerarlos es trabajo del coordinador.**
- El mapa de la catedral (`tools/bake_cathedral_kit.py`, `make_cathedral_map()`) dibuja las lancetas y el umbral con rosetón. El comentario de la línea ~565 dice «at world Y=1056 each cycle». En el C, `generate_band()` elige la fila del mapa con `band * 16 % map_h_tiles`. Tienes que **demostrar con números** en qué Y absoluta cae el rosetón dentro del sistema de `godrays.c` (Y absoluta = Y de mundo + desplazamiento acumulado). Los números de banda crecen hacia arriba en cada rebase; revisa `strip_start()` y `strip_rebase_if_needed()`.
- Con la marea visible, todos los haces se ocultan (`tide_visible`). Esa regla se mantiene.

## Pasos

1. Escribe en la entrega la cuenta que relaciona la Y absoluta de `godrays.c` con la fila del mapa del kit, para lancetas y rosetón. Si las lancetas actuales **no** coinciden con los vanos dibujados, dilo antes de seguir.
2. Separa en `godrays.c` los dos emisores:
   - **Lanceta:** periódica, cada 256 px, lado alterno, siempre con variante de lanceta.
   - **Rosetón:** uno por ciclo de 1.024 px, en el arco del crucero, haz frontal hacia abajo y centrado en x=256. Si el gráfico del haz de rosetón está pensado para entrar de lado, usa la pieza tal cual, centrada, y anótalo como provisional: el arte final no es de esta sesión.
3. **Prioridad:** al dibujar una pantalla (superior o inferior por separado), si el rosetón cae en el rango visible, se saltan todos los haces de lanceta de esa pantalla.
4. Mantén los topes `GODRAY_OAM_LIMIT` y `GODRAY_PIECE_LIMIT`, sin bucles sin tope ni `float`. Las divisiones por periodo siguen con `floor_div` y potencias de dos (usa desplazamientos donde se pueda).
5. Test de host con contrato de texto, `tests/test_godrays_emitters_contract.py`: no hay `% GODRAY_RAY_COUNT` para elegir variante; existe la prioridad del rosetón; no hay `float`. Declara el test en `hostTests`.
6. Escenario `scenarios/godrays_rose_priority.json` con la variante `cathedral-playground`. Usa poke de jugador para colocar la cámara: (a) frente a una lanceta, fuera del crucero; (b) con el rosetón en pantalla. Capturas con nombres veraces: `lanceta_lateral_con_haz` y `roseton_sin_haz_lateral`. **Calcula las Y con la cuenta del paso 1** y recuerda que un poke por debajo de y=768 provoca un rebase de 512 px.

## Criterio de aceptación (lo comprueba el coordinador)

- Build `cathedral-playground` y `cathedral-playground-perf` sin warnings nuevos; tests de host PASS; escenario PASS.
- En las capturas, el haz de lanceta sale del vano dibujado en el muro. Con el rosetón visible solo hay un haz, el frontal.
- Medición en la DS con `PERF_PROFILE` (regla 6): sin frames de más de un vblank atribuibles a godrays.
