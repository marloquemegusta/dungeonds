# STATUS.md - Estado Actual e Historial Reciente de DungeonDS

Primero el estado necesario para retomar el trabajo sin depender del chat; después, las entregas recientes verificadas (más nueva primero). El historial hasta 2026-11-18 está en `STATUS-ARCHIVE.md`.

## Estado actual (2026-11-19)

**Qué es hoy el juego** (detalle en `DESIGN.md`, «Estado vigente»): la ROM por defecto es el Acto I por encuentros: salas hechas a mano con barrera que se abre al limpiarlas, pasillo con relicario (un Don por relicario, reliquia en el relicario dorado y al vencer a cada jefe) y El Abanderado como jefe (stage 5, repetido en el 10 y el 14). Sin marea, sin horda continua, sin gemas ni experiencia. El héroe carga el rayo y, al volver a pulsar, la carga empieza al instante (no hay recuperación tras disparar).

**En qué punto está:**
- Método de diseño sala a sala (`DESIGN.md` §6.13.10): hecha la primera vuelta del Ojo táctico y la guarnición; siguen la procesión ligera, el balcón y la primera sala media.
- Stats del rayo (`feat/stats-rayo`, 2026-11-19, a probar en la DS): carga base 0,8 s, alcance base 110, Prisa −10 por rango hasta carga 8 (`DESIGN.md` §6.12.10); retirada la recuperación muerta del código.
- Sin programar: atrio, flanqueo coordinado de los Exvotos, invocador, catálogo v3, Campanero, El Paso y los actos II y III.
- Sin medición `perf` en la DS del último ciclo (intro, coberturas, Ojo táctico).
- Remate (`L`): la embestida previa y la cámara pegada al héroe se probaron a mano con buena pinta (`feat/remate-tuning`, 2026-11-18); falta un testeo más a fondo del balance de alcance, tambaleo, feedback y recarga, sin pasada de escenarios ni medición `perf` en la DS.

**Fallos y deuda conocidos** (una sola lista; detalle técnico en `TECHNICAL.md` §4):
- `test_bestiary_assets_contract` falla: `tools/gen_bestiary_exvoto.py:23` apunta a un worktree borrado (`exvoto-anim`).
- 4 escenarios `enemy_ojo_*` fallan por expectativas desfasadas (heredado de `main`): `esquiva_saliendo_de_la_linea` y `heroe_entra_en_la_llamarada` piden `nav_y` con 0,5 px de diferencia; las dos `llamarada_pasa_*` piden estado del cargador 12 y sale 14.
- `encuentros_smoke` falla en el relicario (sin diagnosticar; no se sabe si ya fallaba antes).
- `scenarios/intro_tarjetas.json` (5 tarjetas) desfasado frente a las 6 de la ROM; no verificado.
- La rotura del relicario se ve poco porque la oferta de Don la tapa.
- Ganchos de prueba por retirar cuando la variante de encuentros sea el único juego: `g_enc_debug`, bot de encuentros, `g_abc_debug`, `g_upg_debug`.
- Data abort intermitente en hardware, sin causa conocida (`TECHNICAL.md` §4.4).

### Entregas recientes (más nueva primero)

- **Limpieza de documentación (`docs/limpieza-docs`, 2026-11-19):** `DESIGN.md` refleja el juego actual (relicarios: 13 pasillos, 12 Dones y 1 Reliquia dorada; Cireneo 4 y Abanderado ~37 disparos; sin marea, horda, gemas ni XP), `STATUS.md` y `TECHNICAL.md` recortados con lo histórico en `STATUS-ARCHIVE.md`, `LORE.md` sin la Marea y regla nueva en `AGENTS.md`: al cerrar cada sesión se revisan los MDs. Borrados legacy (sprites `marine`/`necron`/`charger`, briefs de encuentros, `scenarios_legacy`, test de golpes con armas antiguas). Solo docs; sin build. [`walkthrough`](walkthroughs/limpieza-docs/walkthrough.md).

- **Intro: seis tarjetas con clips grabados en escenas montadas (`feat/intro-tarjetas`, 2026-11-19, integrado en `main`):** la intro tras NUEVA PARTIDA enseña La catedral, Moverse y apuntar, Coberturas, Rematar, Relicarios y Vida, con textos que aclaran las invulnerabilidades del remate y del golpe. Los clips se graban en escenas exactas del sandbox (`tools/clip_scene.py`) y de la ROM `encuentros` (relicario), con fundido de 3 imágenes al cerrar el bucle. Las ROM de captura sandbox ya no llevan «Nv.» ni barra; el Makefile ya no activa `ENCOUNTERS_PROTO` en ellas. Los relicarios ya no curan. **Pendiente:** ver «Fallos y deuda conocidos». [`walkthrough`](walkthroughs/intro-tarjetas/walkthrough.md).
- **Ojo táctico, guarnición y Ojo en todas las salas (`feat/ojo-alcance`, 2026-11-19, integrado en `main`):** primera vuelta del método sala a sala (`DESIGN.md` §6.13.10), jugada en la DS con el usuario. **Cambia:** el Ojo no tiene alcance (solo le corta la vista una columna o estatua); un Ojo en todas las salas del acto I (7 Ojos nuevos en ligeras y medias); guarnición arriba (Exvotos y Cireneos que esperan junto al Ojo y se sueltan al acercarte, al dañarlos o al morir su Ojo); el Ojo es un tirador táctico en las salas de encuentros: cubierto tras banco o saco espera sin disparar y, al salir, arranca el ciclo normal de apuntado; tras columnas y estatuas te sigue y se recoloca (correa que crece hasta toda la sala). **No cambia:** las salas siguen siendo las plantas v2 (el catálogo v3 es solo diseño); el flanqueo coordinado de los Exvotos no está programado; el Ojo anda a un tercio de tu velocidad y mantiene la línea solo ~57 % del tiempo con el héroe moviéndose (palancas pendientes: velocidad de persecución y tiempo parado al apuntar); el comportamiento de la horda no se toca. **Sin hacer:** medición `perf` en la DS (rayo largo y búsqueda cada 8 frames por Ojo; el usuario no notó tirones); la última versión, con ciclo completo al salir de cobertura, no se jugó en la DS. Build 0 avisos; escenarios del Ojo y de cobertura baja PASS tras actualizar dos a propósito (`enemy_ojo_andar_mirar_sentenciar`, `cobertura_baja_agachado`); `test_guardrails` PASS. **Deuda heredada:** los 4 escenarios `enemy_ojo_*` que fallan, en «Fallos y deuda conocidos». [`walkthrough`](walkthroughs/ojo-tactico/walkthrough.md), registro en [`plan_pruebas.md`](walkthroughs/sala-atrio/plan_pruebas.md).
- **Tipografía: Palatino nítida en todo el texto del juego (`feat/tipografia`, 2026-11-19, integrado en `main`):** la poca legibilidad venía de dibujar Georgia suave y recortarla a blanco y negro; ahora se usa el trazado nítido de la fuente. Palatino 11 sustituye a Georgia en el Códice y a la fuente 5×7 en mayúsculas del menú, la pausa, los controles y el HUD de partida (con tildes y minúsculas); los nombres de pedestales llevan tilde y la fila VIDA/VELOC./AMENAZA cabe con marcas más juntas. El contador de FPS queda fuera. Además la ROM jugable vuelve a abrir en el menú de título (el salto venía de la variante de encuentros; ahora solo `SKIP_TITLE` en variantes de pruebas). Decisión en `DESIGN.md` §6.11.2. Build 0 avisos; subida a la DS; sin medir rendimiento por decisión del usuario. [`walkthrough`](walkthroughs/tipografia/walkthrough.md).
- **Códice con datos de juego (`docs/codice-datos`, 2026-11-19, integrado en `main`):** las fichas de Exvoto, Cireneo, Ojo y Abanderado enseñan `VIDA`, `VELOC.` y `AMENAZA` (1-5, el Exvoto es el mínimo de las tres), `HACE` y `TRUCO`. Decisión en `DESIGN.md` §6.11.1; textos acortados para caber. Pendiente: ficha del Monaguillo cuando exista su lore. [Walkthrough](walkthroughs/codice-datos/walkthrough.md).

### Notas técnicas
- Arquitectura, presupuestos y mediciones vigentes (CPU 1,58 ms de media en la DS, tiles 948/1024, EWRAM 3,38 de 3,5 MiB): `TECHNICAL.md` §3.3. Diagnóstico en la DS: `PERF_PROFILE` (`include/perfprof.h`, `fat:/dungeonds_perf.log`) y `crashlog` (`CRASHLOG_ENABLED`); ambas apagadas por defecto, se leen con `fetch-device-log.ps1`.

### Siguientes pasos
1. **Probar los stats del rayo en la DS** (`feat/stats-rayo`) y ajustar carga base, alcance y Prisa.
2. **Seguir el método sala a sala** (`DESIGN.md` §6.13.10): partida de referencia, después la procesión ligera, el balcón y la primera sala media.
3. **Contenido que falta para una partida completa:** actos II y III, Campanero y El Paso, escenario que cambia tras cada jefe (`DESIGN.md` §6.13).
4. **Retirar ganchos de prueba** cuando la variante de encuentros sea el único juego.

Deuda del motor sin prioridad: timestep y lo anotado en `TECHNICAL.md` §4.5.

### Ramas aparcadas
- Solo existe `origin/feat/v03-mazmorra` (WIP de 2026-11-04/05, sin probar en la DS). Borrar el 2026-12-06 si no se ha usado.
