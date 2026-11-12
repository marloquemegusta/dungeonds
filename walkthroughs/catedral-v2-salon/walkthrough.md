# Catedral 0.3.2 v2: planta de salón, muro nuevo, lápidas v5, compositor por pantalla y rebase sin tirones

Fechas: 2026-11-11 y 2026-11-12. Rama `feat/distribucion-catedral`, sobre el commit `dcec825` del compositor v1 (`walkthroughs/distribucion-catedral/`).

## Qué se hizo
- **Criterio estético único.** Todo se ve con la cámara del juego. Se descartan los alzados frontales pintados en los muros, el rosetón visible y el crucero. Planta de salón: muros rectos y continuos, con columnas en línea paralela a cada muro. Las vidrieras no se dibujan; se ve su luz entrando desde la cara del muro. Decisiones en `DESIGN.md` §6.9.1b («Planta, muros y luz» y «Compositor v2»).
- **Editor de planta** (`tools/catedral_editor/editor.html`, generado con `build_editor.cjs`). Estampa las piezas reales sobre el carril e incluye el muro, los haces de luz y las lápidas encajadas en el damero. Guarda en el navegador, en JSON y en PNG. El usuario diseñó con él el recorrido de referencia (`walkthroughs/distribucion-catedral/assets/diseno_usuario_v1.json`) y de ahí salieron las reglas del compositor v2.
- **Muro.** El módulo 3D `gothic_arch` del usuario, renderizado en el lab con la cámara y la luz oficiales (48 px de ancho, periodo de 128 px, espejo en el muro derecho). Sustituye al muro y las lancetas que se pintaban por código.
- **Lápidas v5.**
  - La piedra tallada sustituye a un bloque entero de losas del damero (3×2 o 2×1), en cruz y en caballero.
  - Van a ras del suelo, con los surcos oscurecidos por oclusión ambiental horneada, y se leen desde los pies.
  - Hay dos estampas por lápida, una por cada color del damero, así que encajan en cualquier posición de las juntas.
  - Proceso y lecciones en `tools/catedral_editor/gen/README.md`.
- **Compositor v2** (Python y C, con test de paridad).
  - Bloques de 2 pantallas.
  - Una columna por pantalla y lado, con velas al pie.
  - Pantallas de bancadas (dos grupos de 4 bancos con 24 px de paso; el marine cabe entre ellos) o de relicario con velas, al azar.
  - Lápidas sueltas y en escalera.
  - Fuera de la demo quedan bancos rotos y volcados, columna rota, santo, sacos y crucero. Los assets de sacos se conservan.
- **Godrays.** Un haz por pantalla, con lado y altura por hash, saliendo de la cara del muro (x = 48 / 208; antes, 16 / 240, del muro de 16 px).
- **Rebase de la tira.**
  - Ahora desplaza 768 px (múltiplo de los bloques).
  - Se quitó un congelado de ~2,5 s: el `qsort` de los runs de oclusión degeneraba con datos casi ordenados.
  - El estado posterior se prepara por trozos en los frames previos, así que el cambio cuesta un frame normal.
  - Ya no vacía la caché de tiles del fondo, lo que causaba un frame con tiles equivocados (parpadeo).
- **Limpieza de assets.** Se retiraron 372 archivos viejos: suelos de prueba, la copia de seguridad de sombras, 28 lápidas viejas y scripts que ya no se usan. Lápidas y muros definitivos en `assets/environment/cathedral/{lapidas,muros}/`.

## Verificación
- **Tests de host:** 13 en verde. Incluyen la paridad del compositor C/Python, la equivalencia bit a bit del rebase preparado frente al anterior (2 semillas × 20 rebases, preparado completo, a medias y sin preparar) y el orden de la oclusión.
- **Compilación:** 0 warnings en las variantes `default`, `cathedral-playground`, `cathedral-playground-perf` y `godrays`.
- **Escenarios (emulador), 8 en PASS:**
  - `strip_rebase_sin_congelar` (nuevo);
  - `strip_climb_smoke`, `strip_cathedral_look`, `catedral_ciclo_capturas` y `godrays_demo`;
  - `cathedral_props_depth_collision`, `cathedral_bench_collision` y `cathedral_playground_respawn`.
- **Presupuesto:** kit de 857 de 1.024 tiles, peor ventana 379 de 440 y RAM principal 2.416 de 4.096 KB, antes de añadir los ~90 KB de los búferes de preparación.
- **DS real** (`cathedral-playground-perf`, `PERF_PROFILE` solo en esa variante; el valor por defecto sigue en 0):
  - Peor frame del juego: 406.000 ticks, un 72 % de los 560.190 del presupuesto. Media: 26 %.
  - Ningún frame perdido por trabajo del juego. Los ~25 frames perdidos por minuto coinciden con la escritura del log en la SD (~30 ms cada una); la única ventana sin escritura no perdió ninguno.
  - Rebase: preparación de 75.000–81.000 ticks por trozo; cambio de 282.000.
  - El pico de subida de tiles del fondo bajó de ~250.000 a ~50.000 ticks.
  - El usuario confirma que ya no parpadea.

## Evidencia visual
- [`assets/rom_ciclo_capturas.png`](assets/rom_ciclo_capturas.png): ROM real en el emulador. Nave libre, bancadas, relicario y estado tras el rebase.
- [`assets/kit_preview.png`](assets/kit_preview.png): el kit horneado (muro nuevo, columnas y grupos de bancos).
- [`assets/lapidas_v5_ejemplos_x3.png`](assets/lapidas_v5_ejemplos_x3.png) y [`assets/lapidas_editor_v5.png`](assets/lapidas_editor_v5.png): lápidas v5 sobre el suelo y colocadas por el editor.
- [`assets/diag_antes_ahora.png`](assets/diag_antes_ahora.png) y [`assets/lapidas_diagnostico_ok.png`](assets/lapidas_diagnostico_ok.png): diagnóstico del encaje. La retícula de juntas que se usaba (16/16) estaba desplazada respecto a la real (22,5/16,5).
- [`assets/camara_juego_A_B.png`](assets/camara_juego_A_B.png): por qué los muros no muestran sus arcos con la cámara del juego.
- [`assets/rebase_parpadeo_antes.png`](assets/rebase_parpadeo_antes.png) y [`assets/rebase_parpadeo_despues.png`](assets/rebase_parpadeo_despues.png): frames alrededor del rebase, antes y después de quitar el vaciado de la caché.
- [`assets/editor_haces.png`](assets/editor_haces.png): el editor con los haces saliendo de la cara del muro.

## Pendiente
- **Pausa en el emulador.** Tras el rebase, el marine queda quieto 3 frames en DeSmuME. No es un `hitstop` y en la DS el frame sale barato; el usuario no lo nota.
- **Escenario `godrays_gif`:** no revisado.
- **TECHNICAL.md:** no describe todavía el rebase preparado (búferes de reserva, `strip_prepare_step`, 768 px).
- **Variedad y escala.** Escala general de las piezas, caballero más legible (modelo más simple) y variedad de tramos: siguientes sesiones.

## Lecciones
- **Medir antes de corregir.** Medir la retícula en la imagen, en vez de fiarse de una fórmula heredada, resolvió el encaje de las lápidas tras varios intentos fallidos. El diagnóstico con un bloque de color plano lo hizo evidente.
- **Leer la memoria del juego.** Un escenario que lee variables internas (`s_next_band`, `s_shift_total_px`) encontró el congelado del rebase en minutos.
- **El emulador no es la DS.** El congelado no se veía en DeSmuME tras el primer arreglo, pero en la DS seguía costando 56–88 ms. Regla 6.
- **Descartar los tirones de medición.** En la ROM de medición, los tirones pueden ser de la escritura del log en la SD: hay que separar las ventanas con `sdw_ticks` antes de concluir.
