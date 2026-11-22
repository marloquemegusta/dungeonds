# Puñetazo andando (ARPG)

Rama `fix/punch-pies-puños` sobre `proto/arpg`, 2026-11-22. Worktree `.worktrees/fix-punch-pies`.

## Problema
El combo de puñetazos se dibujaba con un clip de pies plantados. Andando, el clip se desplazaba con el héroe y los pies deslizaban. La primera corrección (enraizarlo durante el golpe) quitaba el deslizamiento pero rompía el kiteo, que es una mecánica central del ARPG.

## Decisión
`DESIGN.md` §7.2: el héroe puede andar mientras pega, al `65 %` de su velocidad. El tren superior reproduce el clip del golpe y las piernas el clip de andar en la dirección real de movimiento; la cadencia del paseo se alarga en la misma proporción para que la zancada cuadre con el avance. Parado, el golpe se reproduce entero con los pies plantados. Andando, el golpe va en la dirección de movimiento y solo alcanza un cono frontal de `±45°` (a menos de `4` px entra siempre); parado, mantiene el autoapuntado al enemigo más cercano.

## Implementación
- `include/punch.h`: `PUNCH_WALK_SPEED_PCT 65` y `PUNCH_WALK_SPLIT 16`; `punch_start`/`punch_try_chain` reciben `soft_lock`.
- `source/punch.c`: con `soft_lock` apunta al enemigo más cercano; sin él, pega en `hero_dir` y filtra el objetivo por el cono frontal. El daño se aplica al mismo enemigo que fijó la dirección.
- `source/main.c`: durante `punch_active()` se permite andar a `PUNCH_WALK_SPEED_PCT` y se escala `current_period` (`4 → 6`); se deja de congelar `s_player.frame`/`is_moving`.
- `draw_punch`: composición en runtime en un canvas `48x48`. Por encima de `PUNCH_WALK_SPLIT` (`16` px sobre los pies) copia el fotograma del golpe; por debajo, el del andar, desplazado por el delta de anchors y centrado. Se recompone solo cuando cambia el fotograma de golpe o el de andar. Buffers estáticos: ~4,6 KB de píxeles + ~2,4 KB de runs.

## Verificación
- Build `default` con 0 warnings nuevos.
- Escenario `scenarios/punch_andando.json` PASS:
  - andar normal: `0,637 px/frame` vertical con período `4` → ~`20,4 px` por ciclo;
  - golpe andando: `0,414 px/frame` (65 %) con período `6` → ~`19,9 px` por ciclo. La zancada cuadra, no desliza;
  - `punch=1` y `moving=1` durante el golpe; `punch=0` al acabar;
  - parado: `py` constante durante todo el golpe (`punch=1`, `moving=0`).
- GIFs de la ROM real a 4x y 33 ms: [andando](assets/punch_andando_4x.gif) y [parado](assets/punch_parado_4x.gif). Hojas de contacto: [andando](assets/punch_andando_sheet.png) y [parado](assets/punch_parado_sheet.png).

## Pendiente
- Medición `perf` en la DS: la composición solo se rehace cuando cambia un fotograma, pero no se ha medido en hardware.
- Base de compilación: el tip de `proto/arpg` no compila por sí solo porque la sesión de SFX/remates tiene cambios sin commitear en `.worktrees/arpg`. Para verificar se copiaron temporalmente esos ficheros al worktree y se restauraron; el commit de esta sesión lleva solo este cambio.
