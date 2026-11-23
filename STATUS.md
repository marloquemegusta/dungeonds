# STATUS.md - Estado Actual e Historial Reciente de DungeonDS

Primero el estado necesario para retomar el trabajo sin depender del chat; después, las entregas recientes verificadas (más nueva primero, como mucho ~6; las anteriores pasan a `STATUS-ARCHIVE.md`). Es el estado del juego de `main` (Acto I por encuentros); el prototipo ARPG tiene el suyo en `STATUS-ARPG.md`. Este archivo es idéntico en `main` y `proto/arpg`.


## Estado actual (2026-11-22)

**Qué es hoy el juego** (detalle en `DESIGN.md`, «Estado vigente»): la ROM por defecto es el Acto I por encuentros: 15 stages en 3 actos (4 encuentros + 1 jefe), salas hechas a mano de 2 pantallas con barrera que se abre al limpiarlas, 14 pasillos con relicario normal (1 Don por pasillo), El Abanderado como jefe (stages 5, 10 y 15) con relicario dorado en su sala al vencerlo (1 Reliquia) y Altar en el pasillo final («Fin de la demo»). Sin marea, sin horda continua, sin gemas ni experiencia. El héroe carga el rayo y, al volver a pulsar, la carga empieza al instante (no hay recuperación tras disparar).

**En qué punto está:**
- Método de diseño sala a sala (`DESIGN.md` §6.13.10): hecha la primera vuelta del Ojo táctico y la guarnición; siguen la procesión ligera, el balcón y la primera sala media.
- Stats del rayo (`feat/stats-rayo`, 2026-11-19, a probar en la DS): carga base 0,8 s, alcance base 110, Prisa −6 frames por rango hasta carga 8 (`DESIGN.md` §6.12.10); retirada la recuperación muerta del código.
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

- **Vídeo de lore 05 Sor Leonor, A/B clásico frente a Remotion (2026-11-23, en `main`):** `assets/videos/lore01_05_sor_leonor.mp4` (62,1 s) y `lore01_05_sor_leonor_remotion.mp4` (mismo audio y planos; subtítulo palabra a palabra, zoom por plano y golpes; composición `Lore05` en `C:\codexlocal\devlog`). El Ojo hace de Tribunal y Leonor sale como monja de cera; pregunta «¿Mintió Leonor… o mintió el farol?». Se publican las dos como A/B; resultado pendiente en `lote-01.md`. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **ROM más ligera: cartas y Códice comprimidos (`perf/rom-compresion`, 2026-11-23):** el arte de las 17 cartas de mejora y los retratos del Códice va comprimido (formato de la BIOS) y se descomprime al cargarlo; mismos píxeles. ROM 10,4 → 9,6 MB. Build 0 avisos, `bestiary_tour` PASS y cartas vistas en la ROM; sin mirar en la DS. Siguientes candidatos (remates, sprites a paleta, sombras a 1 bit) en el [`walkthrough`](walkthroughs/rom-compresion/walkthrough.md).
- **Vídeo de lore 10 No es mi corazón (`docs/video-corazon`, 2026-11-22):** `assets/videos/lore01_10_no_es_mi_corazon.mp4` (66,1 s, con voz, sin publicar; textos de los posts en `lote-01.md`). Pregunta moral «¿Quién está más vivo: el que murió o el que lo lleva?», arranque con el corazón de un soldado muerto, Inés como pista final y la cita de Martín sobre el corazón. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **Ejecución del Ojo del Tribunal, re-render con el lab rápido e integración en la ROM (`feat/remate-ojo`, 2026-11-21):** el gesto aprobado (el héroe le arranca el farol del hombro, lo tira y lo patea; el cuerpo descabezado se incorpora a su postura encorvada y cae de espaldas, soltando la cabeza que lleva en la mano) se ha **vuelto a renderizar con el lab rápido** (nuevo `tools/lab/fast/export_scene_fast.cjs`, secuencias GLB de escena, 8 direcciones × 39 fotogramas en ≈15 s) y **está en la ROM**: nuevo `REMATE_KIND_OJO` (celda 96×96, 38 fotogramas, 4 ticks = ~2,5 s, restos = el cadáver). Mismas reglas que el resto: el Ojo tambalea al 50 % de vida, `L` a ≤96 px, invulnerable durante la ejecución, muerte limpia, rayo recargado y restos. Los bins se leen de NitroFS **fotograma a fotograma** (buffers de 23,5 KB; EWRAM 3,32/3,5 MiB, heap 181 KB — el bin entero habría roto la intro). Escenarios de transición del remate PASS. [`walkthrough`](walkthroughs/remate-ojo/walkthrough.md).
- **Huella exacta de las barricadas de sacos (`fix/sacos-hitbox`, 2026-11-21):** la colisión de los sacos es ahora la franja de apoyo de 4 px del arte 3D, no el rectángulo del placeholder: el héroe se pega a la base por delante y por detrás. [`walkthrough`](walkthroughs/sacos-hitbox/walkthrough.md).
- **Render rápido de personajes (`perf/render-rapido`, 2026-11-21):** exportador sin navegador (`tools/lab/fast/`, Node + rasterizador por software) por defecto en `rebuild_all.py`: 16 personajes 113 s → 29 s con 4 en paralelo (≈2–4 s cada uno solo). Validado a ojo por el usuario. Detalle en [`walkthroughs/render-rapido/`](walkthroughs/render-rapido/walkthrough.md). Regla en `AGENTS.md` (12).


### Notas técnicas
- Arquitectura, presupuestos y mediciones vigentes (CPU 1,58 ms de media en la DS, tiles 948/1024, EWRAM 3,38 de 3,5 MiB): `TECHNICAL.md` §3.3. Diagnóstico en la DS: `PERF_PROFILE` (`include/perfprof.h`, `fat:/dungeonds_perf.log`) y `crashlog` (`CRASHLOG_ENABLED`); ambas apagadas por defecto, se leen con `fetch-device-log.ps1`.

### Siguientes pasos
1. **Probar los stats del rayo en la DS** (`feat/stats-rayo`) y ajustar carga base, alcance y Prisa.
2. **Seguir el método sala a sala** (`DESIGN.md` §6.13.10): partida de referencia, después la procesión ligera, el balcón y la primera sala media.
3. **Contenido que falta para una partida completa:** actos II y III, Campanero y El Paso, escenario que cambia tras cada jefe (`DESIGN.md` §6.13).
4. **Retirar ganchos de prueba** cuando la variante de encuentros sea el único juego.

Deuda del motor sin prioridad: timestep y lo anotado en `TECHNICAL.md` §4.5.

### Ramas aparcadas
- `feat/lighting-modes` (worktree `.worktrees/lighting-modes`, 2026-11-20): variante `lighting` con 3 modos re-renderizados (Día, Atardecer, Noche) y cambio de dirección de sombras en caliente con `SELECT` desde NitroFS (incluye sprites de remates). Sobre todo para probar y comparar diferentes iluminaciones; **pendiente de mergear**.
- Solo existe `origin/feat/v03-mazmorra` (WIP de 2026-11-04/05, sin probar en la DS). Borrar el 2026-12-06 si no se ha usado.
