# v0.2: mazmorra de manadas, modificadores y HUD de run

Rama `feat/v0.2` (parte de `feat/v0.1`). Decisión de diseño en `DESIGN.md` §5.

## Por qué
La v0.1 se jugó en la DS: el francotirador se sentía bien, la escopeta menos, y el conjunto era fácil y poco divertido. Con 3–7 enemigos en una sala cerrada no había fantasía de segar ni progresión. El usuario eligió limpiar una mazmorra de manadas (Diablo) con compromisos y modificadores que invitan a repetir (Isaac/Hades), con reinicio total al morir.

## Qué hay
- **Mapa:** una mazmorra de 768×768 con seis salas (una inferior grande y tres superiores con puertas), seis zonas de color con neones de acento. Generada con el pipeline lab → baker, sin Blender. Con las sombras del lab (la misma luz key que los personajes) y brillo de neón delante de los muros. La primera versión salía plana, sin sombras ni luz: el export las desactivaba y el shadow camera del lab, de ±5 m, solo cubría el centro del mapa; ahora se ensancha en el export. 999 tiles únicos (máximo 237 por ventana de 33×25, presupuesto 440), 3133 runs de oclusión, unos 83 KB en ROM. [Imagen horneada](assets/mapa_mazmorra_horneado.png).
- **Manadas:** 6 manadas, 22 enemigos. Estado `DORMANT` hasta que el jugador queda a menos de 220 px de suelo de un miembro o se daña a uno; entonces despierta toda la manada. [Todos dormidos al empezar](assets/inicio_manadas_dormidas.png) y [la manada despierta](assets/manada_despierta.png).
- **Al limpiar una manada:** cura 1 golpe y salen dos pedestales ([captura](assets/pedestales_tras_limpiar_manada.png)); coger uno quita el otro y muestra su nombre ([captura](assets/modificador_cogido.png)).
- **Modificadores (8):** perdigones perforantes, recámara doble, gatillo ligero, cañón largo, sed de sangre, coraza ósea, pies ligeros, retroceso brutal. Todos con ventaja y coste (tabla en `DESIGN.md` §5), leídos por `weapons.c`, `gameplay.c` y `main.c` a través de `g_mods`.
- **HUD de la run:** vida, modificadores, `MANADAS n DE m` y nombre del modificador cercano; banner "MAZMORRA COMPLETADA" al terminar. Siempre visible, pantalla inferior.
- **Arreglos de la v0.1:** los proyectiles enemigos se ocultan tras los muros (se dibujaban encima) y tiradores y cargadores miran hacia donde caminan.

## Decisiones que conviene revisar
- La luz del mapa (`lighting` en `arenas.json`) no es la del resto del lab, solo la dirección de la key; ver `TECHNICAL.md` §3.
- Escenarios de la v0.1 ligados a las arenas viejas se borraron; los de disparo, arma y pantalla superior siguen pasando. `bone_dismemberment_preview` dependía de un botón que ya no existe y se borró.
- El atajo de depuración L+R+X ahora mata la manada más cercana (a través de `enemy_hit`) en vez de vaciar la arena.

## Rendimiento medido en la DS (primera ROM de la v0.2, `PERF_PROFILE 1`)
- 12360 frames: CPU media 199.000 ticks (35,5 % de 560190), máximo 682.182 (121,8 %), 110 frames con más de 1 vblank (0,89 %).
- Tramo sostenido de ventanas 116–124 con CPU media de 300–411 k ticks: enemigos (`en`) 55–60 k y sprites (`blit`) 63–74 k por frame, con varias manadas despiertas.
- Dos picos aislados por encima del presupuesto (ventanas 97 y 201). No certifica 60 FPS todavía (`AGENTS.md` regla 6); hay que bajar el coste de `en`/`blit` en combates con varias manadas.

## Feedback del usuario tras jugarla en la DS
Más divertida que la v0.1; gráficos bien y sombras coherentes. Pendientes: tuning de daños y stats, modificadores poco claros, pedestales y UI cutres, mazmorra más grande y con salas más diferenciadas (puertas). Detalle en `DESIGN.md` §5. El log de la última ROM no se pudo leer (FTP cerrado).

## Validación
- `build-project.ps1`: DS_BUILD=PASS.
- Todos los `tests/test_*.py` en OK, incluidos los nuevos `test_modifiers_contract` y `test_encounters_contract` reescrito.
- Escenarios `dungeon_pack_wakes_near_player` y `dungeon_pack_reward_pedestals` en DeSmuME (capturas arriba).
- **Pendiente:** jugar en la DS y certificar 60 FPS con `PERF_PROFILE` (hasta 24 enemigos, dos pantallas, navegación 48×48 sin medir todavía). Ver `AGENTS.md` regla 6.
