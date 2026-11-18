# Walkthrough — Ejecuciones del Exvoto y Cireneo (`feat/remate`)

**Fecha:** 2026-11-18  
**Rama:** `feat/remate`  
**Diseño:** `DESIGN.md` §6.13.8 («Remates / Glory Kills»)

## Qué se ha hecho

1. **Mecánica de remate (Glory Kill) unificada en C para Exvoto y Cireneo:**
   - **Detección de golpe no letal:** Un impacto que no mata deja al enemigo en estado de tambaleo (`ENEMY_STATE_WOBBLE`) durante 60 frames (~1 s), con un pulso cálido de luz (marfil/ocre).
   - **Activación por botón L:** Si el héroe pulsa `KEY_L` a distancia de cuerpo a cuerpo (≤ 48 px), se inicia la animación de remate combinada.
   - **Invulnerabilidad y control:** Durante la animación, el héroe es invulnerable y no se puede mover ni disparar; la cámara acompaña al actor y los enemigos no atacan al ejecutado.
   - **Recompensa instantánea:** Al terminar la ejecución, el rayo láser queda recargado al instante (`weapons_ready_instant()`), listo para disparar en cuanto el jugador recupere el control.
   - **Restos:** El Exvoto deja las dos mitades de cera partidas en el suelo parpadeando durante 0,5 s antes de desaparecer.
2. **Animaciones de ejecuciones elegidas (Sonnet Opción A):**
   - **Exvoto (Opción A):** El héroe lo alza por las muñecas y lo parte en dos en vertical (celda 64×64, 12 fotogramas).
   - **Cireneo (Opción A):** El héroe le arranca la cruz de la espalda, salta y lo atraviesa contra el suelo con ella (celda 80×80, 12 fotogramas).
3. **Optimización de memoria EWRAM para encajar en la Nintendo DS:**
   - La celda de 80×80 del Cireneo incrementaba el consumo en EWRAM desbordando el límite estricto de 3,5 MB de la consola.
   - Se optimizó `tools/generate_remate_sprites.py` compartiendo máscaras de sombra cada 2 fotogramas y reutilizando los fotogramas finales de reposo del Cireneo, reduciendo el tamaño total en más de 63 KB y asegurando la compilación limpia sin avisos en la ROM de producción.

## Verificación

- **Compilación:** `DS_BUILD=PASS` (0 warnings).
- **Subida por FTP a Nintendo DS física:** verificada y aprobada por el usuario (`ftp://192.168.1.151:5000/roms/nds/dungeonds.nds`, 9.213.952 bytes).

## Evidencia

- Comparativa de opciones de diseño: `walkthroughs/remate-exvoto/remate_ronda2.html`
- GIFs de variantes en `walkthroughs/remate-exvoto/assets/ronda2/exvoto_A.gif` y `cireneo_A.gif`.
