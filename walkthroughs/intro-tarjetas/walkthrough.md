# Tarjetas de introducción: seis clips grabados en escenas montadas (`feat/intro-tarjetas`, 2026-11-19)

Tras NUEVA PARTIDA la intro enseña seis tarjetas, cada una con un bucle de la pantalla inferior grabado de la ROM y un texto corto (`source/intro.c`).

## Qué cambia
- **Tarjetas:** La catedral, Moverse y apuntar, Coberturas, Rematar, Relicarios y Vida. El texto de Rematar dice que la ejecución y el segundo posterior dan invulnerabilidad y que el rayo queda recargado; el de Vida, que tras un golpe hay un segundo de invulnerabilidad (60 frames, comprobado en el código).
- **Clips en escenas montadas:** el sandbox coloca al héroe y a los enemigos en coordenadas exactas, con la regla 5 comprobada (`tools/clip_scene.py`: conversión mundo-pantalla del mapa strip y comprobación de encuadre). Apuntar, Coberturas (el Ojo apunta desde arriba a través de un bloque de bancos y el héroe se agacha tras ellos sin daño), Rematar (Exvoto con 250 PV, disparo real, L) y Vida salen de las ROM `cathedral-sandbox` y `remate-sandbox`. Relicarios sale de la ROM `encuentros` (campo de depuración `start_up4` y `dbg_relic_x/y` también en la variante normal).
- **Bucle:** los clips acaban con una disolución de 3 imágenes hacia el principio (61 de acción + 3 de fundido; límite `VID_MAX_N` 64).
- **ROM de capturas:** sin «Nv.» ni barra de experiencia (`source/main.c`, solo `cathedral-sandbox` y `remate-sandbox`).
- **Makefile:** las variantes sandbox ya no activan `ENCOUNTERS_PROTO` por error (`DEFINES` y `CFLAGS`).
- **Relicarios ya no curan corazones** (`ENC_HEAL_EVERY` eliminado del generador y de las tablas).

## Evidencia
Capturas de la ROM por defecto (pantalla superior = vídeo, inferior = texto), una por tarjeta, en `assets/`: `1_catedral.png` … `6_corazon.png`. Los GIF y las hojas de contacto están en `artifacts/intro_clips/` (no versionado).

## Verificación
- Build `cathedral-sandbox`, `remate-sandbox`, `encuentros` y por defecto: 0 avisos nuevos.
- Cada clip pasa su escenario con aserciones de estado; `--verify-bin` decodifica los seis.
- Tests de host: 17 PASS y 1 FAIL ajeno (`test_bestiary_assets_contract` busca una hoja de sprites en el worktree `exvoto-anim`, que ya no existe).
- Sin medición `perf` en la DS: no se toca render ni bucles de juego, solo depuración y la intro.

## Limitaciones conocidas
- La rotura del relicario se ve poco: la oferta de Don la tapa enseguida.
- El Ojo de Coberturas queda en el borde superior del encuadre.
- El texto de Coberturas nombra los sacos: en la ROM por encuentros agachan (`ENC_R_SACOS`); en el mapa strip de las ROM de captura son decorado.
- `scenarios/intro_tarjetas.json` (5 tarjetas) queda desfasado; la captura de las seis está en `scenarios/intro_tarjetas_capturas.json`.

---

## Entrega anterior (primera versión de las tarjetas, conservada)

## Tarjetas de introducción (`feat/intro-tarjetas`, 2026-11-15)

Al elegir `NUEVA PARTIDA` se muestran 4 tarjetas antes de empezar: La catedral, Moverse y apuntar, La marea y Vida. Decisión en `DESIGN.md` §6.3.

![Las 4 tarjetas](assets/tarjetas_resumen.png)

- **Arriba:** bucle de vídeo de la pantalla inferior del juego real (256x192, 30 imágenes/s, sin pérdida) cargado bajo demanda desde NitroFS (`nitrofiles/intro/*.bin`, 828 KB en total; la ROM pasa de 5,19 a 6,03 MB). Se regenera con `tools/gen_intro_clips.py`.
- **Abajo:** título, texto y botones `< Ant`, `Saltar`, `Sig >` (`Empezar` en la última). Lápiz, cruceta, `A`/`B` y `L`/`R`; `Saltar` o `START` empiezan la partida. No sale al reiniciar desde la pausa.
- **Verificación:** compilación 0 warnings, host 21/21, escenario `intro_tarjetas` PASS (píxeles superiores idénticos a los clips). Validado en DS física por el usuario (sin registro de rendimiento).
- **Pendiente menor:** los bucles de las tarjetas 2, 3 y 4 saltan de golpe al reiniciar; compresión con pérdida descartada.
