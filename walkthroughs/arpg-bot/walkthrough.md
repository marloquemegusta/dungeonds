# Bot probador del ARPG (v2: campaña, perfiles de nivel y panel de balance)

Variante `arpg-bot` (`build-project.ps1 -Variant arpg-bot`): un piloto automático juega la catedral del ARPG como una persona de nivel configurable
(torpe / normal / bueno). Solo sustituye botones y lápiz; el juego no lo sabe. No existe en la ROM normal (`ARPG_BOT` vale 0 por defecto).

## Qué hay
- **Campaña:** el bot hace bajadas por el camino principal (Nave 1 a 4 y Cripta). Cuando baja de su umbral de vida y no hay un orbe de vida cerca, abre la pausa
  y elige «Volver al campamento» con las teclas de verdad; en el campamento camina al jergón, duerme (sube de nivel solo ahí, reaparecen los enemigos),
  camina a la puerta y entra por el último altar. Si muere, pulsa la pantalla de muerte hasta llegar al campamento. Termina al vencer al jefe, a los 90 minutos
  de juego (324000 frames) o al tope de bajadas. Toca los altares al llegar a una sala sin enemigos despiertos.
- **Modos** (`ArpgBotDebug.mode`): 0 una bajada sin retirada (hasta morir o vencer al jefe), 1 campaña, 2 una bajada que acaba cuando se retira.
- **Nivel fijo:** `start_level` arranca la bajada con la vida y el maná de ese nivel (fórmulas de `arpg.h`, vía el panel). Sin equipo de referencia (inventario base).
- **Combate:** rodea a los grupos de cuerpo a cuerpo si hay camino libre (`kite_dist`), reserva maná para el Ojo y el Cireneo (`mana_reserve`), usa el rayo siempre que
  compense, y no huye de enemigos que no pueden alcanzarlo (muro de por medio). Si se mete sin querer en una galería lateral, sale por donde entró.
- **Panel de balance** (`g_bal`, `include/arpg_balance.h`): una estructura global con los valores de `arpg.h` por defecto (sin escribir nada, el juego es idéntico):
  vida y daño por tipo de enemigo, XP por tipo y factor de la curva, vida/maná del héroe (base y por nivel), coste y daño del rayo, daño de puñetazos,
  probabilidades y cantidades de la cura del remate, densidad de grupos, jefe, nivel 2 del Ojo/Cireneo, regeneración de maná. Los escenarios lo escriben por
  desplazamiento antes de jugar, sin recompilar.
- **Estadísticas** (`g_arpg_bot_stats`): por bajada (frames, sala más profunda, nivel al empezar, causa del final, daño recibido), pantallas recorridas y tiempo por sala,
  segundo en que llegó a cada nivel, maná gastado, resultado del jefe.
- **Modo rápido** (`fast`): no dibuja la escena (la emulación va ~2x más rápida). Comprobado: la misma campaña con y sin dibujo da las 195 estadísticas idénticas.

## Cómo se usa
`python tools/arpg_balance.py [--config lote.json] [--set hp_pct.SHOOTER=80] [--jobs 3]` escribe los escenarios, los lanza en paralelo, imprime la tabla contra los
objetivos de `DESIGN-ARPG.md` §9 con PASS/FAIL y añade una línea a [balance_log.md](balance_log.md). `--emit-scenarios` reescribe `scenarios/arpg_bot_{torpe,normal,bueno}.json`
(una bajada de nivel 1 sin retirada, con capturas). Detalle de la configuración en la cabecera del script.

## Evidencia
- [bot_campana.gif](assets/bot_campana.gif): retirada por el menú de pausa, paseo al jergón, dormir (sube a nivel 2), paseo a la puerta y nueva bajada (ROM real, 4x, ~15 fps de captura,
  mostrado al doble de velocidad para que pese menos de 8 MB). Escenario: `scenarios/arpg_bot_gif_campana.json`.
- [bot_normal.gif](assets/bot_normal.gif): perfil normal en la Nave 1 y cruce de la puerta (de la v1).

Documentos: `DESIGN-ARPG.md` §9 (objetivos de balance) y la línea del remate (cura al instante, patch aparte). `TECHNICAL.md` y `STATUS-ARPG.md` no cambian en esta pasada (herramienta de prueba).
