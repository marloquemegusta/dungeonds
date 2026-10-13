# Handoff: WH40K, arena sintética de colisiones

Fecha: 2026-10-13  
Propósito: permitir que otro LLM continúe el diagnóstico sin depender del historial del chat.

## Estado actual

- Repo: `C:\codexlocal\dungeonds`.
- Worktree activa: `C:\codexlocal\dungeonds\.worktrees\wh40k-floor-preview`.
- Rama: `feat/wh40k-floor-preview`.
- No hacer reset, checkout destructivo ni limpieza: el worktree contiene muchos cambios sin commit de trabajo anterior y artefactos. Revisar `git status --short` antes de editar.
- Se diseñó una arena pequeña con cajas/paredes programáticas sobre el suelo real WH40K. Usa una copia del motor C actual y el pipeline de Blender → render BG → mapas de colisión/oclusión → ROM.
- ROM de arena subida a la Nintendo DS por FTP el 2026-10-13. Resultado confirmado por el script: `FTP_UPLOAD_RESULT=PASS`.
- Destino DS: `ftp://192.168.1.151:5000/roms/nds/dungeonds.nds`.
- ROM local: `artifacts\collision-arena\collision-arena.nds`, 2.187.776 bytes, CRC DeSmuME `2C0163BA`, SHA-256 `32460815AAF6204C421B32E09571659B21C766608B6C49567AE179D6BA94EF3F`.
- **Falta que el usuario pruebe esta arena en la DS y reporte el resultado.** Las pruebas disponibles son de DeSmuME; no afirmar todavía que el comportamiento físico en DS se haya confirmado.

## Qué intenta resolver el proyecto

El usuario reportó que el Charger y otros personajes llegan a edificios y, según el punto y la dirección, el movimiento se detiene mientras se siguen viendo los pies por debajo del muro; en otros casos el actor parece flotar o quedar dibujado por encima del edificio. Los síntomas varían al aproximarse desde sur, norte y laterales. El usuario sospecha que collider y oclusión podrían estar desplazados o calcularse con convenciones distintas. Es una pista útil, no una causa demostrada.

El objetivo inmediato ya no es ajustar a ciegas los FBX originales: es decidir de forma reproducible si el defecto nace en el bake offline (geometría y datos generados) o en cómo el motor usa esos datos online. La arena reduce el problema a formas conocidas y rutas cardinales medibles.

## Contexto de iteraciones anteriores

El hilo comenzó con una cámara que dejaba de seguir al jugador hacia un borde aparente, aunque el mapa visible continuaba. Después se reportó que el mapa se cortaba en esquinas, el fondo fuera del suelo debía ser negro e intransitable, y la pantalla superior debía mostrar la continuación de la inferior. Hubo varias revisiones del tamaño, escala, máscara de suelo y repetición del mapa. El usuario insistió correctamente en que el mundo debe conservar su escala y su borde cuadrado en coordenadas del mapa, cuya proyección se ve como un rombo/cuadrado isométrico; no debe sustituirse por un octógono ni rellenarse el vacío con suelo inventado.

Al ampliar el mundo repitiendo sectores, las colisiones de edificios empeoraron. Se corrigieron pases de colisión y se enviaron varias ROMs, pero el usuario siguió viendo atravesamiento parcial y pies visibles debajo de muros. También se probaron correcciones distintas por dirección de aproximación; resolver una dirección pareció empeorar otras. En una explicación anterior se atribuyó el bloqueo a una torre central sin evidencia suficiente; no repetir esa suposición. Las capturas y el comportamiento que describa el usuario tienen prioridad sobre conjeturas visuales.

El usuario ha pedido reiteradamente que se compare con el comportamiento anterior que funcionaba y que no se declare arreglado basándose solo en una captura parecida. Hasta que la arena y los assets originales se validen, tratar el fallo como abierto.

## Diseño de la arena

Cambios en `tools\assemble_wh40k_full_sector.py`:

- Flag `WH40K_COLLISION_TEST=1` activa el modo arena; `WH40K_OUTPUT_ROOT` permite generar salidas aisladas.
- La producción mantiene constantes explícitas de cuatro sectores: `MAP_SEGMENTS=4`, mundo `3200×1920 px`, `ORTHO_SCALE=187.5`.
- La arena usa un sector de `1280×768 px`, `ORTHO_SCALE=75`, rejilla de colisión `320×192` y spawn `(640,384)`. Conserva la densidad original aproximada de `17,07 px/m`.
- Carga los tres GLB de suelo WH40K reales y reemplaza solo los props FBX por ocho cajas/cubos 3D cerrados. Incluye paredes con orientaciones 0°, 45°, 90°, 135° y 150°, alturas 1,2–3,6 m, tramo corto, esquinas y pilar.
- Las posiciones se colocan convirtiendo coordenadas de pantalla mediante la matriz de cámara Blender real. Hay una ruta de prueba UP/RIGHT/DOWN/LEFT desde el spawn.
- Mantiene cámara, iluminación, render, generador de tiles BG y formato de colisión/oclusión del proyecto. El código C del motor se copia al proyecto temporal para compilar la arena sin reemplazar el mapa normal.
- El desplazamiento de sectores en modo producción conserva literalmente `segment * 50.0 - 75.0`; solo la arena usa el centrado dependiente de su cantidad de sectores.

La arena y la ROM están dentro de `artifacts\collision-arena\` (ignorado por Git). Evidencia conservada y versionable:

- `walkthroughs\wh40k-collision-arena-test\walkthrough.md`
- `walkthroughs\wh40k-collision-arena-test\assets\01_blender_arena_bake.png`
- `walkthroughs\wh40k-collision-arena-test\assets\02_baked_collision_overlay.png`
- `walkthroughs\wh40k-collision-arena-test\assets\03_ds_low_wall_stop.png`
- `walkthroughs\wh40k-collision-arena-test\assets\04_ds_high_wall_crossing.png`
- `walkthroughs\wh40k-collision-arena-test\assets\05_ds_high_wall_beyond.png`

## Hallazgo medido

**La reproducción en DeSmuME demuestra un fallo offline del bake para las cajas altas de esta arena; no prueba que todos los edificios FBX originales tengan exactamente la misma causa.**

El generador obtiene el canal de caminar con un rayo vertical que empieza en `SIDEWALK_Z + 1.20 m` y recorre `1.19 m` hacia abajo. En cajas cerradas de más de 1,2 m, el origen cae dentro del volumen y la cara inferior queda justo fuera de la distancia del rayo. El bake no marca esas celdas como `COLL_WALK`. La pared de 1,2 m sí deja marcas caminables. El motor online bloquea la pared baja cuando recibe esos flags, por lo que su lectura básica del canal WALK sí está operativa.

Resultado observado del array horneado: 62 celdas walk-only vinculadas a la pared baja; las paredes altas no reciben las marcas WALK previstas (aunque aparecen en el canal sólido/de proyectil). El overlay permite comparar salida visual y canales generados.

Resultados DeSmuME de la ROM final (`2C0163BA`), después del preflight de botones:

| Dirección | Geometría | Resultado medido |
| --- | --- | --- |
| UP | Pared horizontal, 1,2 m | Se detiene: `y` pasa de 98304 a 86539; el contador `blocked_moves` crece durante la espera y `moving=0`. |
| RIGHT | Pared vertical, 2,4 m | Atraviesa y sigue avanzando; `blocked_moves=0`. |
| DOWN | Pared diagonal, 3,6 m | Atraviesa; `blocked_moves=0`. |
| LEFT | Pared diagonal, 1,8 m | Atraviesa; `blocked_moves=0`. |

La oclusión se hornea por separado. Estas sondas no demuestran todavía que el orden de oclusión, el anclaje de los pies ni las máscaras de profundidad sean correctos en todos los ángulos. La arena está pensada para observar ambos canales con geometría controlada.

## Flujo offline/online que debe conservarse en el diagnóstico

**Offline:** Blender importa el suelo y las paredes; el script renderiza el color/fondo y los pases auxiliares. De esos datos genera tiles BG y arrays C de suelo, colisión y profundidad/oclusión. El array empaquetado queda en headers/fuentes que entran en la ROM.

**Online:** el motor proyecta la posición del personaje y consulta el suelo/canal `COLL_WALK` al intentar moverlo; si la celda no está marcada, puede cruzar. El render del actor consulta/procesa oclusión por separado para decidir qué partes del sprite quedan delante o detrás de los edificios. Colisión y oclusión no son la misma prueba y pueden fallar de forma independiente.

Por eso, comparar el PNG de la escena, el overlay de canales, el estado numérico de movimiento y la captura real del motor es clave. Una imagen por sí sola no basta para atribuir el origen.

## Verificación y fallo de suite

- Build BlocksDS de la ROM temporal: PASS.
- Preflight de entrada para la ROM final: PASS.
- Escenarios DeSmuME cardinales UP/RIGHT/DOWN/LEFT: ejecutados; resultados detallados arriba. Los escenarios de las paredes altas son probes de fallo, así que su PASS significa que reprodujeron el atravesamiento, no que estén arregladas.
- `tests/test_world_void_contract.py`: 7 tests PASS, incluido el contrato de escala del mapa.
- La suite completa `scripts/run-host-tests.ps1 -ProjectPath .` no termina verde: `test_sprite_ground_anchor.py::test_player_and_enemy_frames_use_exported_ground_anchor` falla porque espera el texto `py - PLAYER_ANCHOR_Y + min_y`, mientras que el código actual usa `py - s_char_ground_anchor[...] + min_y`. La suite también ejecutó correctamente `test_bone_lance_contract.py` (3 tests), `test_fbx_bg_generator.py` (3) y `test_world_void_contract.py` (7). No se modificó ese test ni se debe mezclar su arreglo con el diagnóstico de colisión sin comprobar primero cuál contrato es el correcto.
- `git diff --check`: limpio; solo avisa de normalización LF/CRLF en `STATUS.md` y `walkthroughs/README.md`.
- Graphify fue actualizado después de modificar código. Reportó advertencias de extracción por recursión/sintaxis en algunos archivos C; el comando terminó con exit 0.
- El script de subida completó FTP con `FTP_UPLOAD_RESULT=PASS`; esta es la ROM temporal de arena, no la ROM normal del mundo completo.

## Reproducción y archivos útiles

Proyecto temporal con código y configuraciones copiadas del motor actual:

```powershell
& .\scripts\build-project.ps1 -ProjectPath .\artifacts\collision-arena
& .\scripts\run-scenario.ps1 `
  -RomPath .\artifacts\collision-arena\collision-arena.nds `
  -ScenarioPath .\artifacts\collision-arena\scenarios\collision_arena_east.json `
  -OutputPath .\artifacts\collision-arena\evidence\east-rerun
```

Escenarios: `collision_arena_input_preflight.json`, `collision_arena_north.json`, `collision_arena_east.json`, `collision_arena_south.json`, `collision_arena_west.json` dentro de `artifacts\collision-arena\scenarios\`.

Para inspeccionar el código y datos del problema:

- `tools\assemble_wh40k_full_sector.py`: creación de arena y pase offline de raycast/canales.
- `artifacts\collision-arena\`: headers/fuentes generados, mapa de colisión, overlay, proyecto copiado, ROM y eventos/capturas de escenarios.
- `source\main.c`, `source\diablo_dungeon.c`, `include\diablo_dungeon.h`: consultas online de movimiento y datos empaquetados del motor normal. Compararlos con la copia dentro del proyecto de arena.
- `scenarios\wh40k_building_collision_contact.json`, `wh40k_charger_building_contact.json`, `wh40k_charger_north_occlusion_probe.json`, `wh40k_charger_side_occlusion_probe.json`: casos previos del mapa/actores originales.
- `walkthroughs\wh40k-floor-preview\walkthrough.md`: historia de mapa, suelo, bordes y entregas anteriores.

El bake de prueba puede regenerarse en Blender llamando al assembler con `WH40K_COLLISION_TEST=1` y `WH40K_OUTPUT_ROOT` apuntando al proyecto temporal. Asegurarse de que `WH40K_ART` apunta a los assets locales que contienen los GLB requeridos; el valor por defecto del script es específico de esta máquina. El proyecto temporal debe tener `source`, `include`, `tools` y `.ds-game-dev` listos antes de generar y compilar.

## Siguientes pasos recomendados

1. Pedir al usuario que pruebe la ROM ya subida en la DS y confirme si las cajas bajas/altas bloquean, si los personajes se ocultan y qué ocurre al acercarse desde las cuatro direcciones. No dar por válida la ROM física hasta tener ese reporte.
2. Si la arena reproduce lo mismo en hardware, corregir primero el bake: la consulta de intersección debe detectar volúmenes sólidos a todas las alturas y orientaciones. Considerar rayos desde arriba hacia abajo, intersección de volumen/celda o rasterizar la huella del collider sobre la rejilla; elegir tras inspeccionar la geometría y convenciones reales. Evitar ampliar ciegamente un margen que pueda clasificar suelo, sombras o interior caminable como pared.
3. Rehornear la misma arena y repetir exactamente los cuatro escenarios. Confirmar los flags WALK en overlay/datos y que los cuatro muros bloquean sin desplazar el collider respecto a la huella visible.
4. Probar aparte oclusión de norte/sur/laterales con actor y muros altos: registrar coordenadas, celda, profundidad del muro, anchor de pies, máscara/flags y orden de dibujo. La expectativa del usuario es que un actor no cruce muros y que sus pies no aparezcan por debajo ni quede flotando encima.
5. Solo después portar el arreglo a los edificios FBX reales, volver a hornear el mundo grande, mantener la escala y los límites cuadrados isométricos, generar ROM y evidencia, y probarla en DS. No volver a cambiar la escala del mapa como compensación del collider.
6. Investigar por separado el fallo del contrato de sprite anchor; no asumir que el test es correcto ni que el código está mal sin revisar historial y comportamiento.

## Criterios de cierre

- Paredes sintéticas de varias alturas y orientaciones bloquean desde los cuatro lados en ROM, sin huecos ni atravesamiento en celdas de borde.
- Las mismas pruebas de render confirman oclusión coherente: pies detrás del muro cuando corresponde; no hay actor flotando ni segmentos que aparezcan por debajo.
- La ROM corregida supera los probes automatizados y el usuario confirma comportamiento físico en la DS.
- El mapa completo conserva escala original, forma cuadrada en coordenadas del mundo, fondo negro no caminable fuera del mapa y continuidad correcta entre pantallas.
- Walkthrough, índice y STATUS se actualizan con resultados observados; distinguir siempre DeSmuME de DS física.

## Nota de colaboración

El usuario está frustrado por explicaciones que parecieron afirmar causas sin prueba y por ROMs que no resolvieron el síntoma. Comunicar hallazgos con medidas/evidencia, separar hechos de hipótesis y no volver a etiquetar una solución como terminada hasta que el usuario la valide en DS.
