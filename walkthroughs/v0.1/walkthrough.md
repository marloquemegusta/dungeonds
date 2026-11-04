# v0.1 - Prueba de diversión mínima

Rama `feat/v0.1`. Implementa `DESIGN.md` §4 por fases. Este documento se amplía con cada fase.

## Fase A - Jugador y armas (+ pantalla superior igual a la inferior)

### Qué cambia
- **Armas:** escopeta y francotirador, munición infinita, definidas por parámetros (`g_weapon_tuning`). Fuera pistola, gatling, pesada, munición, armadura y pickups.
- **Disparo desde el arma:** el lab exporta la boca del rifle por dirección y frame (`dirMuzzle` en `settings.json`, tabla `g_character_muzzle` en C). Perdigones, rayo y fogonazo salen de ahí, a su altura, no de los pies.
- **Escopeta:** un disparo por toque, bombeo, retroceso del jugador, empujón y aturdimiento del enemigo.
- **Francotirador:** toque = apuntar (el jugador se para, láser discontinuo rojo); a los 24 frames el láser pasa a cian y soltar dispara un rayo que atraviesa enemigos; cancelar con L o arrastrando el stylus sobre el personaje.
- **Jugador:** 5 golpes, 60 frames de i-frames con destello rojo, reinicio instantáneo de la arena al morir.
- **Feel:** hitstop de 3-4 frames, temblor de pantalla por arma, FX procedurales (trazos con estela, fogonazo, chispas).
- **Pantalla superior igual que la inferior:** `render_screen` se ejecuta una vez por pantalla (suelo, actores, sombras, proyectiles, FX). El motor secundario reparte su banco C de 128 KiB en 448 slots de tile, el mapa y una página 16 bpp. Para que el suelo quepa, el baker fusiona con pérdida los tiles casi idénticos (3804 -> 1123, peor ventana 576 -> 252). Detalle en `TECHNICAL.md` §3.3.

### Evidencia (ROM en DeSmuME)
- [Disparo en 8 direcciones](assets/faseA_disparo_8_direcciones.png): el fogonazo cae a <= 2,0 px de la boca exportada (`tools/check_shot_origin.py`, escenario `shot_origin_8_dirs`). En el cuadro del Este se ve además el destello rojo del jugador herido.
- [Armas y apuntado](assets/faseA_armas_apuntado.png): escopeta, láser rojo, soltar antes de tiempo sin disparo, láser armado, disparo con estela y cancelación con L (`weapons_switching_and_touch`).
- [Enemigos y proyectiles en la pantalla superior](assets/faseA_pantalla_superior_enemigos.png) (`upper_screen_shows_enemies`).
- [Francotirador apuntando hacia arriba](assets/faseA_francotirador_pantalla_superior.png) (`sniper_aims_upper_screen`).

### Rendimiento en la DS (`PERF_PROFILE 1`, HUD de depuración encendido)
Medido por sesión del log `/dungeonds_perf.log` (el fichero acumula sesiones; hay que separarlas por el reinicio del contador de frames). Presupuesto: 560190 ticks por frame.

| Sesión | Frames | >1 vblank | CPU media / máx (ticks) |
| :--- | ---: | ---: | ---: |
| Prototipo A (línea base) | 2520 | 12 (0,48 %) | 52.920 / 133.255 |
| Fase A, armas y FX | 4980 | 40 (0,80 %) | 97.148 / 163.574 |
| Fase A + pantalla superior completa | 3000 | 17 (0,57 %) | 102.033 / 141.377 |

El segundo pase de render cuesta ~5.000 ticks de media y no añade pérdidas de frame sobre la línea base. Todos los frames pasados son de un solo vblank y la CPU máxima queda muy por debajo del presupuesto, así que la causa no es el cálculo: pendiente de investigar en la Fase E (sincronización con el VBlank).

### Validación
- Build limpia, sin warnings. 13 tests de host. Escenarios `shot_origin_8_dirs`, `weapons_switching_and_touch`, `sniper_aims_upper_screen`, `upper_screen_shows_enemies`, `marine_walk_evaluation` PASS.
- Revisión de código con Sonnet: 9 hallazgos, corregidos 7 (cooldown saltable con L, toque desplazado por el temblor, boca dentro de un muro, hitstop dependiente del orden, parada del francotirador un frame tarde, velocidad espuria tras reiniciar, shadowing). Dos se dejaron a propósito (apuntado que no se arma durante el cooldown; muerte sin feedback por ser instantánea).

### Pendiente de la fase
- Tuning (dispersión de perdigones, longitud del láser) en la Fase E.
- La ROM de la DS lleva el HUD de depuración activable con START; el parpadeo de la pantalla superior (un solo búfer) no se ha podido medir con el log.

## Fase B - Cargador con navegación (DESIGN.md 4.4, 4.6)

### Qué cambia
- **Colisión separada:** `source/collision.c` (`position_is_free`, `bullet_position_is_free`, `sweep_position`, `line_is_walkable`) sale de `gameplay.c`; así la navegación se prueba en el host con la colisión real.
- **Campo de distancias** (`source/navfield.c`): rejilla de 16 px por casilla (96x54) sobre la colisión; BFS incremental con doble búfer (300 expansiones por frame, el campo completo tarda ~10 frames y los enemigos siempre leen uno terminado). Un enemigo baja al vecino de menor distancia; sin esquinas cortadas en diagonal; si su casilla tiene el centro bloqueado (pegado a un muro) sale hacia el vecino alcanzable.
- **Cargador:** `CHASE -> ATTACK(cooldown) -> CHASE`, sin telegraph ni estados de detección. Persecución directa a menos de 48 px con visión y línea transitable; si no, baja por el campo. Muerde a 16 px de suelo solo con línea libre para el cuerpo (los muros bajos no bloquean la visión). Velocidad 293 (90 % de los 326 del héroe). Todos los enemigos actúan desde el spawn.
- **Empujón:** a bocajarro el cargador retrocede ~14 px de suelo y se aturde 10 frames.

### Evidencia (DeSmuME)
- [El cargador rodea la esquina del muro](assets/faseB_cargador_rodea_muro.png): `charger_walks_around_wall` lleva al jugador, con el recorrido calculado por el propio BFS (`tools/gen_charger_wall_scenario.py`), a una casilla que el spawn no ve; el cargador llega y muerde. Este mapa solo tiene un rodeo de 41 px.
- [Empujón de la escopeta](assets/faseB_empujon_escopeta.png): `charger_shotgun_shove`; el cargador pasa de y=60,5 a y=53 (≈ 7 px de pantalla, 14 de suelo) y retoma la persecución.
- Test de host (`tests/test_navfield.py`, gcc sobre el mapa real): 1041 casillas caminables todas alcanzables, el gradiente lleva al objetivo en exactamente `d` pasos sin pisar muros, el campo incremental iguala al de una pasada y las 389 casillas de centro bloqueado junto al suelo tienen salida.

### Revisión de código (Sonnet)
Sin fallos de memoria ni carreras. Corregidos: casilla propia con centro bloqueado (el cargador dejaba de seguir el campo), objetivo elegido por orden de vecinos en vez de por cercanía, mordisco y aproximación directa a través de muros bajos, comentario del presupuesto (~10 frames, no ~4). Pendiente de medir en la DS: coste de `nav_update` (estimado ~6 % del frame, Fase E).

## Fase C - Tirador necrón (DESIGN.md 4.5)

### Qué cambia
- **FSM:** `POSITION -> TELEGRAPH -> BURST(3) -> COOLDOWN -> POSITION` (fuera `IDLE`, `ALERT`, `SEARCH`, `AIM` y los campos de detección). `ENEMY_STATE_CHASE` pasa a valer 0.
- **Banda de distancia** `[56, 104]` px de suelo: retrocede si el jugador está más cerca, se acerca si está más lejos o sin tiro limpio (recto si el cuerpo puede caminarlo, si no por el campo de navegación) y hace strafe entre medias (perpendicular en el suelo 2:1; invierte si choca). Durante la pausa entre ráfagas sigue moviéndose.
- **Telegraph:** 18 frames (0,3 s) quieto, con un destello verde que parpadea más rápido y más grande en la punta del arma (misma tabla de bocas que el jugador).
- **Ráfaga:** 3 proyectiles lentos (1,5 px/frame) que salen de la boca a su altura, apuntados con lead de la mitad del desplazamiento previsto del jugador. El lead anterior se dividía entre 256 (no existía). Solo telegrafía con línea de bala limpia (`bullet_line_is_free`).
- **Proyectiles:** cabeza, cuerpo verde y cola corta, dibujados a la altura de la boca; golpean con una elipse en métrica de suelo; un golpe resta un punto de vida. Pool de 32.
- Un empujón de la escopeta cancela un telegraph o una ráfaga en curso (contrajuego).

### Evidencia (DeSmuME)
- [Telegraph y ráfaga](assets/faseC_tirador_telegraph_rafaga.png): destello en la punta del rifle y tres proyectiles en línea hacia el jugador (`shooter_telegraph_burst`). Con una captura cada 4 frames, la cabeza de proyectil pasa de 2 a 4 y 6 píxeles (1, 2, 3 proyectiles) y el ciclo se repite cada ~140 frames = posición 30 + telegraph 18 + ráfaga ~20 + pausa 70.
- [Mantiene la distancia](assets/faseC_tirador_mantiene_distancia.png): con el jugador avanzando hacia ellos durante 240 frames (`shooter_keeps_distance`, modo dios) los tiradores dan vueltas por los flancos sin dejarse pisar.
- `tests/test_shooter_contract.py` (11 pruebas sobre el C real) sustituye al test espejo `test_enemy_fsm.py`, que modelaba una FSM que ya no existe.

### Revisión de código (Sonnet)
Sin fallos graves. Corregidos: pool de proyectiles (16 -> 32), disparo que nace dentro de un muro (arranca en los pies), empujón que cancela el telegraph, parpadeo de frame al empezar el destello. Sin tocar: tirador que sigue disparando si el jugador se esconde durante la ráfaga (las balas mueren en el muro) y un posible vaivén en la banda si existieran celdas que bloquean balas pero no cuerpos (no hay en este mapa; se comprobará con las arenas).

### Pendiente
- Tuning de banda, velocidad y cadencia en la DS (Fase E).

## Fase D - Arenas (DESIGN.md 4.6)

### Decisiones (sesión de diseño con el usuario, 2026-11-03)
Arenas de 384×384 px (dos pantallas de alto, 1,5 de ancho), una forma distinta cada una (sala con 2 pilares, muros bajos, dos pasillos, sala grande con pasillo central), composición de DESIGN (3 cargadores / 3 tiradores / 3 tiradores lejos + 1 cargador / 3 cargadores + 4 tiradores) y paso automático con pausa de medio segundo. Detalle en `DESIGN.md` §4.6 y `assets/arenas/arenas.json`.

### Qué cambia
- **Assets:** `tools/make_arena_glb.py` (escritor GLB propio, sin Blender), `tools/export_arenas.py` (lab headless, recorte 384×384 de un render de 896×541 porque el lab encuadra por la caja envolvente del modelo girado), paquetes en `assets/sprites/arenas/`. El export mide <= 1 px de error contra la especificación y la rejilla de colisión coincide con suelo menos bloques.
- **Baker** `tools/bake_arena.py` (sustituye a `bake_isometric_shooter_bl.py`): un `source/arena_0N.c` por arena (paleta propia, tiles con presupuesto, colisión, oclusión, inicio y enemigos) y `source/arenas.c`. Cada arena usa 49-72 tiles (la peor ventana, 26-49) y ~60 KB de fuente; la ROM baja de 1,9 MB a 1,4 MB.
- **Runtime:** `include/arena.h` + `g_arena`; colisión, visión, oclusión, fondo, navegación (32×32 casillas máx.) y cámara leen de la arena activa. Encuentros por arena (`encounters.c` reescrito, sin plantas, drops ni portal de salida), reinicio de la arena al morir y paso a la siguiente con fundido a negro.
- **Cámara:** sin salir de la arena en horizontal; el jugador siempre en la pantalla táctil (puede apuntar hacia arriba), con a lo sumo media pantalla de vacío fuera.
- **Depuración:** L+R+X limpia la arena (para escenarios).
- **Retirado:** el mapa `isometric_shooter_bl` del build, sus tablas generadas (`diablo_dungeon`, `dungeon_bg_tiles`, `dungeon_occlusion`) y los 5 escenarios atados a él.

### Evidencia (DeSmuME)
- [Render de las 4 arenas en el lab, con inicio y spawns](assets/faseD_arenas_render_lab.png).
- [Cadena 1 -> 2 -> 3 -> 4 -> 1](assets/faseD_cadena_4_arenas.png) (`arena_chain`, con L+R+X): cada arena con su forma y su composición. La caída de brillo entre arenas se midió en la captura (de 147 a 24 y de vuelta).
- [Oclusión tras un pilar y cargadores rodeándolo](assets/faseD_oclusion_pilar.png) (`arena_pillar_occlusion`).
- 17 tests de host, entre ellos `test_arena_export` (geometría), `test_arena_data` (inicio y spawns libres, composición) y `test_navfield` (compilado con gcc sobre las 4 arenas: spawns alcanzables, suelo conexo).

### Limitaciones conocidas
- Las arenas son un blockout liso (suelo y cajas grises, sin decoración); sirven para la prueba de diversión, no como arte final.
- El suelo no tiene muro frontal ni los adornos del mapa viejo (rayas rosas, conos).
- El primer plano de cada caja (~9 px inferiores) no cuenta como oclusor porque el lab solo cuenta superficies de más de 0,25 m.
- Pendiente de la DS: rendimiento de arenas densas (A4, 7 enemigos) y de `nav_update` con el campo recalculándose continuamente.
