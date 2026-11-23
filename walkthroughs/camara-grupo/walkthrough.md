# Cámara hacia el grupo (2026-11-23)

**Problema:** al kitear (retroceder delante de un grupo que está más arriba), el adelanto de la cámara se iba hacia atrás y dejaba muy poco espacio de pantalla para los enemigos. La excepción existente solo funcionaba con el lápiz tocando por encima del héroe; al levantarlo entre disparos, la vista se deslizaba.

**Decisión (`DESIGN.md` §6.3):** en combate, el encuadre vertical apunta a un punto entre el héroe y el centro del grupo de enemigos despiertos, pesando más los cercanos. Se mueve con suavidad (rápida si está lejos, frena al llegar, máx. 3 px/fotograma) y el héroe nunca sale de la franja 25 %–75 % de la pantalla táctil. Sin enemigos, vuelve el adelanto por marcha, desde donde estaba la cámara y sin salto. Se retira la excepción de kiteo por lápiz.

**Qué cuenta como combate:** enemigos activos y vivos que no estén dormidos, rezando, suspendidos, siendo rematados o muertos (la cámara queda quieta durante el remate).

**Código:** `source/main.c`, `update_camera_group()` (una pasada por los enemigos y una división por fotograma); `update_camera_lookahead()` sin el parámetro de apuntado.

**Verificación:**
- Build normal, `perf` y `encuentros` con 0 avisos.
- Probado por el usuario en la DS (ROM `perf`): le gusta cómo se siente.
- Medición en la DS (`dungeonds_perf.log`, 125 ventanas de 1 s): CPU media ~12 % del presupuesto; 2 ventanas con un pico breve por encima (1–2 fotogramas cada una), en la línea de partidas anteriores.
- Sin escenarios: el cambio es de encuadre y se validó jugando.
- Sin capturas: el comportamiento se aprecia jugando, no en una imagen fija.

Los MDs cambiados (`DESIGN.md`, `STATUS.md`, `STATUS-ARCHIVE.md`) se sincronizan con `proto/arpg`, que recibe también el código.
