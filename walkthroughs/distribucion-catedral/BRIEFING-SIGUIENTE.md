# Briefing para la siguiente sesión: lo que falta para terminar el escenario de la catedral

**Punto de partida:** rama `feat/distribucion-catedral` (sin commit) con el compositor de la nave funcionando. Lee antes [`walkthrough.md`](walkthrough.md) y `DESIGN.md` §6.9.1b (bullet «Compositor de la catedral»).

**Reglas de la casa que aplican** (`AGENTS.md`): decisión de diseño escrita antes del código (regla 9), 60 FPS certificados en la DS y no en el emulador (regla 6), subida a la DS solo con confirmación del usuario (regla 7), cada agente con modelo asignado en el plan (Haiku para leer, Sonnet para análisis, DeepSeek flash para implementación acotada, siguiendo lo que el usuario pidió en esta sesión).

## Orden recomendado

| # | Paso | Bloquea | Quién decide |
|---|---|---|---|
| 1 | Medir y cerrar esta rama | todo lo demás | usuario (confirmar subida a la DS) |
| 2 | Muros laterales con módulo 3D | cierre del escenario | usuario (orientación y piezas) |
| 3 | Vela, sombras y lápidas | pulido | usuario (aprobar imagen) |
| 4 | Crucero completo y arco transversal | cierre del escenario | usuario |
| 5 | Escala general de las piezas | pulido | usuario |
| 6 | Presupuesto del kit y godrays | certificación | automático + DS |

## 1. Medir y cerrar esta rama (primero)

**Estado:** el compositor sube la peor ventana de oclusión de 4.117 a 15.624 runs (3,8 veces) por las columnas altas y las bancadas. En el emulador no vale como evidencia. La ROM que hay en la consola es **anterior a todos los arreglos de esta sesión** (bancos a 64 px, sombra cortada, rosetón).

**Qué hacer:**
1. Compilar `cathedral-playground-perf` (`PERF_PROFILE 1`) del worktree y subirla con `upload-rom.ps1` **con confirmación explícita del usuario** (la DS necesita `ftpd.nds` abierto). Decir rama, commit, nombre remoto (`dungeonds.nds`), tamaño verificado y qué debe mirar en la consola.
2. El usuario juega una sección de bancadas, la barricada con enemigos y el crucero.
3. Leer el log con `fetch-device-log.ps1 -RemoteFile /dungeonds_perf.log`: media, máximos y frames con más de un vblank. Presupuesto único: 560.190 ticks. Referencia anterior: media 116.277, máximo 396.970.
4. **Si baja de 60 FPS la tarea queda bloqueada hasta optimizar.** Palancas probables: menos runs de oclusión por columna (la huella de oclusión de `columna_entera` es de 120 px de alto) y reducir bancos por grupo.
5. Dejar `PERF_PROFILE 0` antes del merge.
6. Pendientes de limpieza antes del commit: añadir `assets/environment/cathedral/props/*.fbm/` al `.gitignore` (hoy aparecen tres carpetas de texturas sin seguimiento), revisar `git status` y añadir archivos por ruta (nunca `git add -A`).
7. Con el visto bueno del usuario: commit, merge a `main`, `STATUS.md` y limpieza del worktree (`AGENTS.md`, protocolo de cierre).

**Aprobación visual:** el usuario aún no ha visto la ROM con los grupos de bancos centrados. Enseñar primero `walkthroughs/distribucion-catedral/assets/catedral_ciclo_contact_2x.png`.

## 2. Muros laterales: módulo 3D repetible

**Idea del usuario:** generar con Tripo un módulo 3D de pared gótica y repetirlo en las dos franjas laterales (`x = 0..48` y `x = 464..512`).

**Estado:** el usuario ya ha generado una imagen (arco apuntado entre pilares) y el modelo `gothic_arch` está en `assets/inbox/tripo_convert_f450c095-bf8c-4b93-9016-910075bf2f13.zip` (FBX más texturas). **Sin procesar.** No sé si se creó con la imagen vertical corregida; hay que mirarlo.

**Lo que hay que saber de perspectiva (deducido de la cámara, falta confirmar con un render de prueba):**
- La cámara mira a lo largo del pasillo, con 30° de elevación y sin giro. Las paredes laterales corren en esa dirección y su cara se ve **de canto**, con ancho cero. Los props se giran 45° para enseñar dos caras; una pared continua no puede.
- El muro actual es arte frontal pintado dentro de la franja de 48 px (las lancetas están de pie, con la punta hacia arriba de la pantalla).
- Por eso el módulo debe renderizarse como **alzado frontal** (cámara ortográfica de cara a la pared, con una leve inclinación hacia abajo), y no con la cámara de los personajes.
- Cada módulo ocupa unos **48 × 128 px, en vertical** (1 : 2,7), apilado cada 128 px. La imagen apaisada 1,7:1 que se generó primero no sirve tal cual: hay que regenerarla en vertical. El prompt corregido está en la conversación de esta sesión y debe guardarse en `assets/environment/cathedral/prompts.md` (Lote 4, `pano_muro_modular`).

**Decisiones del usuario pendientes (escribirlas en `DESIGN.md` antes de programar):**
1. ¿Alzado frontal con el arco de pie (convención de las lancetas), o la pared «tumbada»? Recomendación: de pie.
2. ¿Dos piezas sueltas (pilar y paño, que se colocan a distancias exactas y repiten sin costura) o un módulo único cortado por el centro de los pilares?
3. Dónde va la lanceta y su haz de luz: hoy la ventana ocupa `X = 0..32` con una bahía cada 256 px alternando lado.

**Cómo hacerlo repetible:** Tripo no garantiza extremos idénticos. Comprobar antes la imagen 2D pegando dos copias una encima de otra y otra al lado; montar el módulo en Blender cortando por el centro de los pilares y duplicando; verificar que no hay costura. Después: render de alzado con el lab (pasos 4–6 de `walkthroughs/v032-escenario/BIBLIA.md` §5.2), cuantizar a la paleta compartida y sustituir el arte provisional de `make_cathedral_map()` en el baker. Presupuesto de tiles: hoy el kit está en 851 de 1.024; el muro actual ocupa parte de ellos.

**Qué no tocar a la vez:** la colisión de los bordes (ya implementada: seis tiles de muro por lado sólidos) y el ritmo de los godrays (`GODRAY_PERIOD=256`).

**Sugerencia de reparto:** Sonnet para el análisis del encuadre y el montaje del módulo; DeepSeek flash para integrarlo en el baker con un brief acotado; y el usuario aprueba una hoja de contactos con el muro junto al marine antes de integrar.

## 3. Pulido de piezas

- **Vela:** sigue en 25 px de ancho y 21 de alto (dos tercios del marine). Debe bajar a ~14 px. Falta `vela.fbx` en el repo (los FBX de props están ignorados); el usuario debe reponerlo en `assets/environment/cathedral/props/` o en `assets/inbox/`. Luego `blender -b -P tools/props/prep_props.py -- <raíz> vela`, `python tools/props/prerender_props.py --raw <tmp> vela` y `python tools/props/prop_shadows.py vela`. El `target_width` ya está en 14 en `tools/props/props.json`.
- **Sombras:** la de `columna_entera` es corta porque la retícula solo deja 8 px a la izquierda del fuste. Las de `columna` (rota), `santo`, `relicario` y `sacos` no se regeneraron: solo hay GLB de tres piezas. Revisar si alguna se ve cortada en la ROM y regenerarla.
- **Lápidas:** el kit solo trae `lapida_cruz_h` (las otras no caben en tiles) y el plan coloca 0–3 en 64 bandas. El diseño (§6.9.1b) pide una Vía A de nave ocasional y una Vía B de crucero. Decidir qué variantes entran y dónde.
- **Columnas:** los cuerpos quedan en px 72..112 y 392..432 (eje a 252, 4 px del centro). La colisión es solo la base (16 px). Revisar si se lee bien junto a los muros nuevos.

## 4. Crucero y arco transversal

- Se quitó el rosetón y el umbral pintados en el suelo (decisión de esta sesión). **Hoy el crucero no tiene arco transversal ni rosetón.** `DESIGN.md` lo prevé como pieza vertical de 416 × 64–96 px con el rosetón (64 px, 12 sectores) centrado, en el borde norte del crucero y con oclusión por profundidad. Necesita su propio modelo y sprite.
- **Godrays:** el haz del rosetón no emite y falta la prioridad entre haces (en la pantalla del rosetón no debe dibujarse a la vez un haz lateral). Es el brief 03 de `walkthroughs/catedral-siguientes-pasos/`; sigue válido.
- **Capilla lateral** opcional cada 8–12 pantallas, y cofres o élites en capillas (`DESIGN.md` §6.9.1b): no están implementadas.
- El contenido actual del crucero (dos santos, velas, relicario) es de primera pasada. El usuario no lo ha revisado en detalle.

## 5. Escala de las piezas (el usuario la dejó para otro momento)

Cada pieza se renderizó con un ancho elegido a ojo (columna rota 40 px, banco 72, santo 32, vela 25…). La referencia vigente es 17,9 px/m con el marine de 2 m a 31 px. Midiendo: la columna rota es ~2,2 m de diámetro (el doble de gorda de lo real), el banco ~4 m (real 2,5–3 m), el santo ~4 m. El usuario dijo que no importa que no sea perfecta «mientras no sea ridícula». Solo la vela se considera fuera de rango. Si se aborda: tabla de tamaños reales con un factor común de ampliación para legibilidad (`DESIGN.md` ya permite piezas un 30–50 % mayores) y re-render del lote.

## 6. Presupuesto del kit y certificación

- Tiles: 851 de 1.024. La nota del brief 04 de `catedral-siguientes-pasos` (kit al 100 %) ya no aplica, pero el muro nuevo consumirá tiles: rehacer la cuenta tras integrarlo.
- **Certificación final de rendimiento en DS** con todo integrado (compositor, muros nuevos, godrays) según `DESIGN.md` §6.9.1b.
- `tests/test_strip_kit.py::test_generated_kit_contract` falla desde antes de esta sesión (`map_h_tiles` 8192 frente a 1024) y no está declarado en `hostTests`: arreglarlo o retirarlo.
- La variante `props-showcase` y el escenario `props_showcase_contacts` (brief 01) **nunca se fusionaron**: no existen en esta rama. Es la cobertura estable de colisión de los props; recuperarla de la rama `feat/props-showcase` si se creó, o rehacerla.
- `catedral_ciclo_capturas` es nuevo y vive en `scenarios/`; revisarlo si cambia el plan.

## 7. Variedad y siguientes tramos (0.6, no bloquea el cierre)

Hoy la nave es un ciclo de 4 tramos repetido, a propósito (prefiere repetición coherente). La variedad extra (tramos a mano, biomas, coro, cripta, ábside) está en la hoja de ruta de la 0.6. No hay que añadirla para dar por terminado el escenario del primer nivel.

## Notas operativas para el coordinador

- **Agentes DeepSeek:** el vigilante pausa si el mismo comando falla dos veces seguidas. Decir en el brief la ruta del suelo (`assets/environment/cathedral/floor/rombos_tripo`), que no repita un comando que falle, que escriba sus scripts temporales fuera del repo y que `--mode actual` con las 17 piezas falla a propósito (límite de 1.024 tiles).
- **Reanudar un agente que murió:** `python -I C:\codexlocal\skills\delegate-agents\delegate.py deepseek --resume <run_id> --brief <nota> --cwd <worktree>`.
- **Escenarios:** `run-scenario.ps1 -ScenarioPath scenarios\<nombre>.json -ProjectPath <worktree> -RomPath <ROM de la variante que indica state.elf>`. `strip_cathedral_look` y `catedral_ciclo_capturas` usan la variante `cathedral-playground`; `cathedral_bench_collision`, `cathedral_props_depth_collision` y `cathedral_playground_respawn` usan `cathedral-playground-perf`.
- **Docker:** si no está arrancado, iniciarlo y esperar a que `docker info` responda antes de compilar.
- **Baker:** `python tools/bake_cathedral_kit.py --floor assets/environment/cathedral/floor/rombos_tripo --mode catedral` regenera `source/strip_kit.c`; `--dump-plan <json>` vuelca el plan para tests y escenarios; `--metrics <md>` escribe las métricas.
- **Brief 02** de `walkthroughs/catedral-siguientes-pasos/` (distribución) queda **sustituido** por esta sesión.
