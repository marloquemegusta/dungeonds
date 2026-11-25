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

- **Vídeo de lore 06 Inés (2026-11-25, en `main`):** vídeo CÓDICE · II listo y sin publicar (56,9 s, con voz, estilo A), con la pregunta «¿Encubridora… o madre?». Defectos aceptados: la cita sale en 3 líneas y en el cierre asoma «tu Nintendo DS.» tras PRÓXIMAMENTE (generador clásico, sin tocar). Verificado: fotogramas; nadie ha escuchado el audio final. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **Props por el lab rápido (`feat/props-lab-rapido`, 2026-11-24, en `main`):** los props de la catedral se renderizan sin navegador (`export_prop_fast.cjs`, ≈14× más rápido); 15 piezas con GLB regeneradas (santo, santo_der espejado con la luz correcta, vela, banco_entero, banco_volcado con pose nueva, etc.) y aceptadas por el usuario. Build 0 avisos; host tests del kit, guardrails y strip PASS; captura de la catedral revisada; sin medición en la DS (cambio de herramienta). Falta: las 8 lápidas `_h/_v` siguen sin GLB. **Pendiente de limpieza:** borrar el worktree `.worktrees/props-lab-rapido` y la rama `feat/props-lab-rapido` (ya mergeada; sus assets ignorados ya están en el repo principal salvo los PNG de depuración de paleta, que regenera el bake). [`walkthrough`](walkthroughs/props-lab-rapido/walkthrough.md).
- **Vídeo de lore 11 El Campanero de Ánimas (2026-11-24, en `main`):** dos montajes listos y sin publicar (clásico y Remotion `Lore11`), con la voz de Simón (CÓDICE · VI) y el tañido; la campana sale como plano de objeto con su badajo. `LORE.md` incorpora al Campanero (Simón Requena). Verificado: fotogramas revisados; nadie ha escuchado el audio final. Detalle: [`walkthroughs/lore-lote-01/`](walkthroughs/lore-lote-01/walkthrough.md).
- **Vídeos de lore y devlog: tema visual propio (`feat/video-tema`, 2026-11-24, en `main`):** todos los vídeos usan el mismo estilo de arte del juego: fondo negro, cajas con la piedra del inventario ARPG teñida de rojo y marco dorado, letra Palatino a 1 bit del juego, marfil/oro/ceniza (antes parecían genéricos de IA). Kit en `tools/video_theme/`; `render_guiones.py` y `render_codice_video.py` pintan los textos con él. Verificado con fotogramas y GIF de Lore11 y Devlog1; `render_codice_video.py` solo con sintaxis (necesita ElevenLabs); el proyecto Remotion (fuera del repo) lleva el tema copiado sin commit. [`walkthrough`](walkthroughs/video-tema/walkthrough.md).
- **Cireneo: atasco contra muros y columnas (`feat/cireneo-atasco`, 2026-11-24, en `main`):** si el Cireneo choca con un muro o columna en plena carga, ya no se queda congelado en la primera pose del andar: hace un atasco de 90 frames en tres tiempos (impacto con 6 astillas y polvo apagado desde el punto de contacto, forcejeo de cara al muro alternando poses de carga y telegrafía, liberación con un paso atrás de ~6 px). Reutiliza poses existentes, sin sprites ni memoria nuevos; el aturdimiento por disparo no cambia. Build por defecto y sandbox 0 avisos nuevos, escenario de evidencia PASS. **Pendiente:** medir `perf` en la DS (sin certificar). [`walkthrough`](walkthroughs/cireneo-atasco/walkthrough.md)
- **Ojo del Tribunal: sentencia escrita en el suelo (`feat/ojo-sentencia`, 2026-11-23, en `main` y `proto/arpg`):** el Ojo ya no apunta con banda verde ni dispara un haz: escribe en el suelo una grieta con ojos que te sigue, se fija hasta el muro, cuenta atrás con sus ojos y estalla toda a la vez en llamas verdes; la cabeza solo abre la boca. El daño es esa franja desde sus pies. Builds por defecto y `perf` sin avisos, guardrails PASS, captura de la ROM. **Pendiente:** medir `perf` en la DS (rendimiento sin certificar); los escenarios `ojo-tribunal` ya fallaban antes por aserciones desfasadas. [`walkthrough`](walkthroughs/ojo-sentencia/walkthrough.md)


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
