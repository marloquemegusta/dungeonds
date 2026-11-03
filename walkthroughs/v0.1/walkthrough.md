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
