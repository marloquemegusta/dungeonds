# Catedral 0.3.2: compositor de la nave (columnata, bancadas, barricada y crucero)

**Fecha:** 2026-11-10 / 2026-11-11
**Rama:** `feat/distribucion-catedral` (sin commit al cierre de la sesión)
**Estado:** funcional en ROM y verificado en emulador. **Sin medir en la DS** y sin aprobación visual final del usuario sobre los grupos de bancos.
**Qué falta para dar el escenario por terminado:** [`BRIEFING-SIGUIENTE.md`](BRIEFING-SIGUIENTE.md).

## Qué se hizo

Se sustituyó el reparto aleatorio de piezas (`stamp_band()` tiraba dados por banda y todo salía suelto) por un **compositor determinista**: el número de banda decide qué se coloca y el azar solo elige variantes. Mismo cálculo en Python (`tools/bake_cathedral_kit.py`, `catedral_plan()`) y en C (`source/strip.c`, `catedral_band()`), con test de paridad.

Las reglas están en [`DESIGN.md` §6.9.1b](../../DESIGN.md), bullet «Compositor de la catedral». Resumen:

- **Tramo** de 256 px (2 bandas). **Ciclo de 4 tramos** (1.024 px, unas 5,3 pantallas): bancadas, bancadas, barricada de sacos (o tramo despejado cada tercer ciclo) y crucero.
- **Columnata** continua junto a los muros salvo en el crucero: columna entera (55 %), rota (30 %) o caída (15 %) por hash estable.
- **Bancadas:** dos filas centradas en el eje de la nave (carriles en x_tile 19 y 35, pasillito de 64 px). En cada tramo y cada fila hay **un grupo de 4–6 bancos pegados** (paso de 32 px), escalonados entre las dos filas. 75 % `banco_entero`, 25 % `banco_roto`. El marine puede colarse entre dos bancos de un grupo (decisión del usuario).
- **Barricada:** línea de `sacos` con `banco_volcado` como escombro. **Crucero:** santos, velas y relicario, sin columnas.

## Cambios por área

| Área | Cambio |
|---|---|
| Piezas nuevas | `banco_entero` (64×32), `sacos` (64×40) y `columna_entera` (40×120), renderizadas desde modelos Tripo con el flujo habitual (Blender → lab → sombra). La vela **no** se pudo reducir (falta su FBX). |
| Baker | Modo `--mode catedral`, hornea solo las fases (pieza, fase) que el plan usa; error duro si pasan de 1.024 tiles (antes envolvía en silencio con `& 0x3ff`); fases propias para los bancos (paso de 32 px); recorte del lienzo de los bancos a 32 px; ids de pieza en el kit. |
| Suelo | Se retiró el inlay de rosetón y el umbral gris que cruzaban la nave cada 1.024 px (decisión del usuario, `DESIGN.md`). |
| Sombras | Regenerada la de `columna_entera`, que salía con un corte vertical recto. Es corta por límite de la retícula. |
| C | `stamp_band()` ya no coloca al azar; solapes por tiles no vacíos; `find_stamp(pieza, fase)`. `LAPIDA_DEBUG` y `PROPS_SHOWCASE` siguen compilando. |
| Tests | `tests/test_strip_layout_parity.py` (C == Python con la semilla `0xC0DE1234`), `tests/test_cathedral_kit.py` actualizado. |
| Escenarios | Nuevo `catedral_ciclo_capturas` (8 pantallas). Reescritos `cathedral_bench_collision` y `cathedral_props_depth_collision` sobre piezas reales del plan. `strip_cathedral_look` ajustado al carril libre. |

## Verificación (2026-11-11)

- **Kit:** 851 de 1.024 tiles (antes 1.024 de 1.024 con la otra distribución); peor ventana de 33×25 tiles **351** (< 440); peor oclusión de 16 bandas **15.624** runs (< 32.768; antes 4.117, **sube 3,8 veces**).
- **Build:** `cathedral-playground` y `cathedral-playground-perf` PASS, 0 warnings.
- **Tests de host:** 184 ejecutados. Único fallo, ya existente en `main`: `test_strip_kit.test_generated_kit_contract` (`map_h_tiles` 8192 frente a 1024).
- **Escenarios (5/5 PASS):** `strip_cathedral_look`, `catedral_ciclo_capturas` (ROM `cathedral-playground`); `cathedral_bench_collision`, `cathedral_props_depth_collision`, `cathedral_playground_respawn` (ROM `cathedral-playground-perf`; ojo: sus `state.elf` apuntan a la variante `perf`).
- **Geometría medida:** pasillo central ≥ 56 px y paso lateral ≥ 48 px en toda la tira; huella total 7,44 % del suelo útil; 119 bancos enteros y 34 rotos en 64 bandas. Métricas completas: [`assets/metricas_catedral.md`](assets/metricas_catedral.md).
- **Paridad:** el modo `actual` ya no reproduce el hash anterior (`7a5493c8…`). Es esperable, porque quitar el rosetón cambia el mapa también ahí.

## Evidencia visual

| | |
|---|---|
| Vista previa de 2 ciclos (Python) | [`assets/catedral_ciclos_2048_2x.png`](assets/catedral_ciclos_2048_2x.png) |
| 8 pantallas de la ROM | [`assets/catedral_ciclo_contact_2x.png`](assets/catedral_ciclo_contact_2x.png) · [GIF](assets/catedral_ciclo.gif) |
| Piezas nuevas junto al marine | [`assets/piezas_nuevas.png`](assets/piezas_nuevas.png) |
| Guías de centrado de la bancada | [`assets/catedral_bancada_guias_3x.png`](assets/catedral_bancada_guias_3x.png) |

## Decisiones del usuario durante la sesión

1. Las columnas son periódicas y van sobre todo junto a los muros, y una columna rota es una entera que cayó.
2. Los bancos van en bancadas, no sueltos, con el pasillito entre dos filas; después, **pegados** en la fila y **en grupos de ~5** en vez de filas continuas.
3. Banco entero y sacos como piezas nuevas; la escala general de las piezas se deja para otra sesión, salvo que la vela es demasiado grande.
4. Prefiere repetitividad coherente a variedad sin sentido.
5. El rosetón y el umbral pintados en el suelo se quitan.
6. El marine puede pasar entre dos bancos de un mismo grupo.
7. Los laterales (muros) se hacen con un módulo 3D de pared repetible, no con arte pintado a mano: [`BRIEFING-SIGUIENTE.md`](BRIEFING-SIGUIENTE.md).

## Lecciones de proceso

- La retícula del baker (posiciones múltiplos de 64 px más la fase, cada estampa con el suelo cocido) y los lienzos de sombra anchos limitan la composición mucho más de lo previsto. Se diseñó primero a mano y se descubrió después.
- Un agente que recorta sombras por cuenta propia estropeó la sombra de la columna: el brief pedía «recortar» sin decir que no se admitía un corte visible.
- El vigilante de `delegate.py` pausa si el mismo comando falla dos veces; con DeepSeek ocurrió casi siempre por una ruta mal escrita (`--floor` es `assets/environment/cathedral/floor/rombos_tripo`) o por lanzar el modo `actual` con las 17 piezas, que ahora falla a propósito. Conviene decirlo en el brief.
- Los escenarios `cathedral_*` leen el ELF de su `state.elf`; hay que pasar a `run-scenario.ps1` la ROM de esa misma variante.
- Tras reiniciar la sesión hubo que arrancar Docker Desktop y esperar con una condición antes de compilar.
