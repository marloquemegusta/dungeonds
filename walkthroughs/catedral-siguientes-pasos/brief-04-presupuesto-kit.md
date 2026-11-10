# Brief 04 · Presupuesto del kit y deuda de tests (Luna)

**Rama sugerida:** `perf/kit-catedral` · **Modelo:** `luna` · Independiente de los briefs 01 y 03. Si el brief 02 cambia la colocación, este va antes o después, nunca a la vez.

## Objetivo

1. Bajar el kit de catedral de **1.024 de 1.024 tiles** a **≤ 900**, sin pérdida visible, para dejar sitio al arte definitivo de muros y a piezas nuevas.
2. Arreglar `tests/test_strip_kit.py`, que espera el mapa antiguo de 64×16 tiles y falla con el periodo actual de 128 filas, y declarar en `.ds-game-dev/project.json` los tests de kit que hoy no se ejecutan.
3. Dejar la profundidad de las lápidas en el mismo formato que la de los props (píxeles del sprite).

## Contexto que necesitas

- `tools/bake_cathedral_kit.py`, `build()`: la clase `Tiles` deduplica tiles exactos, con volteos H/V. Al final imprime `tiles: N/1024; worst window: …`. El presupuesto duro: < 440 tiles distintos en cualquier ventana de 33×25 (`TECHNICAL.md` §3.3).
- `tools/bake_arena.py` ya fusiona con pérdida tiles casi idénticos (umbral medio de color 1,0: 3.804 → 1.123 tiles). Reutiliza la idea, no el código a ciegas: aquí los tiles comparten una paleta de 256 colores y hay que comparar en espacio de color (Lab o BGR555 decodificado), no por índice.
- Los tiles de estampa que contienen sombra o bordes de silueta **no** se fusionan con tiles de suelo, porque el contorno de la pieza se notaría. Fusiona solo suelo con suelo y muro con muro, o restringe la fusión por familia.
- Profundidad: `tools/props/prerender_props.py` ya convierte la profundidad a píxeles del sprite (`sprite_depth()`). Las lápidas se regeneran con `python tools/props/prerender_props.py --skip-lab <lápidas…>`, que tira de la caché `%TEMP%\props_raw`. Comprueba antes que la caché las contiene; si no, avisa. Ojo: `props.json` lista muchas lápidas; regenera solo las que existen en `assets/environment/cathedral/props/render/`.

## Pasos

1. Añade la fusión con pérdida a `bake_cathedral_kit.py`, con umbral configurable (`--merge-threshold`, por defecto el que deje ≤ 900). Tiene que ser determinista: el mismo resultado en cada ejecución.
2. Haz que el baker escriba en el comentario de cabecera de `source/strip_kit.c` el total de tiles y el umbral usado.
3. Arregla `tests/test_strip_kit.py` para el contrato actual: `map_h_tiles` entradas por columna y `floor_h_tiles` para la colisión. Declara en `hostTests` los tests de kit que pasen: `test_strip_kit.py`, `test_cathedral_kit.py` y `test_strip.py`.
4. Prepara la regeneración de las lápidas (lista exacta de piezas) y añade al contrato una comprobación de que cada `depth.png` de lápida está en píxeles del sprite (valores ≤ alto del sprite).

## Restricciones

- No cambies colocación, colisión ni oclusión. Las huellas y los runs de profundidad de los props deben quedar idénticos byte a byte en `strip_kit.c`.
- Sin cambios en el runtime C salvo que sean imprescindibles; si lo son, justifícalo.

## Criterio de aceptación (lo comprueba el coordinador)

- El baker informa ≤ 900 tiles, una peor ventana < 440 y la misma cantidad de runs de oclusión que antes.
- Hoja de contacto antes/después de la ventana con más fusiones, a 1× y 4× NEAREST, revisada con el usuario. Si se nota la diferencia, se baja el umbral.
- Build sin warnings nuevos, todos los tests de host declarados PASS y los escenarios de catedral PASS.

## Comandos del coordinador

```powershell
python tools/bake_cathedral_kit.py --floor assets/environment/cathedral/floor/rombos_tripo
python tools/props/prerender_props.py --skip-lab <lápidas>
& "$sk\build-project.ps1" -ProjectPath $p -Variant cathedral-playground-perf
& "$sk\run-host-tests.ps1" -ProjectPath $p
```
