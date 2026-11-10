# Brief 02 · Distribución de bancos y estatuas (Luna, en dos rondas)

**Rama sugerida:** `feat/distribucion-catedral` · **Modelo:** `luna` · **Requisito:** brief 01 fusionado (banco de pruebas de props).

Esta sesión tiene una **puerta de decisión**. Luna no programa la distribución definitiva hasta que el usuario elija una alternativa (`AGENTS.md`, regla 9).

## Paso 0 · Coordinador, antes de llamar a Luna

1. Enseñar al usuario la vista previa actual (`python tools/bake_cathedral_kit.py --floor assets/environment/cathedral/floor/rombos_tripo --preview <scratchpad>\actual.png`) y una captura de la ROM.
2. Preguntarle en lenguaje llano qué no le convence: densidad, piezas sueltas en vez de grupos, estatuas en medio, repetición, falta de pasillos… Anotar la respuesta en el walkthrough de la sesión.

## Contexto que necesitas

- Las reglas ya decididas están en `DESIGN.md` §6.9.1b, Sesión 1:
  - tres corredores libres de ≥48 px (el central apunta a 64);
  - bancos en bloques de 2–3 filas y fuera de los corredores;
  - huella total ≤15 % del suelo útil;
  - barricadas que alternan lado;
  - familias de tramo: nave despejada, nave con barricadas y crucero;
  - un crucero cada 4–6 pantallas (de 192 px).
- Hoy (`source/strip.c`, `stamp_band()`) se colocan de 1 a 4 estampas por banda de 128 px, elegidas por hash entre los 32 stamps. Las lápidas cuentan como un prop más, y solo se evita un carril central de 64 px. No hay bloques de bancos ni familias de tramo.
- `tools/bake_cathedral_kit.py` replica esa colocación en Python (`placements()`, `preview_and_budget()`) para la vista previa y para el presupuesto de oclusión. **La versión en C y la de Python tienen que dar lo mismo.**

## Ronda A · Tres alternativas (solo en la vista previa en Python)

1. Añade a `placements()` un parámetro `mode` con tres modos nuevos, sin tocar el C:
   - **A «bloques de bancos»:** por banda, 0 o 1 bloque de 2–3 bancos apilados (mismo tipo, misma x, pasos de 16 tiles en y si cabe, si no en bandas contiguas) a un lado del corredor central. La estatua o columna solo va pegada al muro lateral (x_tile ≤ 10 o ≥ 54 − ancho).
   - **B «familias de tramo»:** cada 3 bandas (≈ 1 pantalla) se elige una familia: despejada (solo vela o lápida), barricada (bloque de bancos a un lado que alterna con la pantalla anterior) o crucero (sin bancos; estatuas o columnas simétricas a los dos lados).
   - **C «márgenes»:** todo el atrezo alto (columna, santo, relicario) en los márgenes junto a los muros; bancos en filas cortas de 2 en los corredores laterales, sin tocar nunca el central.
2. Cada modo calcula y devuelve: huella total en % del suelo útil por cada 8 pantallas, anchura mínima de cada corredor y peor ventana de tiles y de oclusión.
3. Añade a `main()` el parámetro `--mode {actual,A,B,C}`.

**El coordinador** genera las cuatro vistas previas y una tabla con las métricas, y se las enseña al usuario. **Parar aquí hasta que el usuario elija** (puede mezclar ideas). La decisión se escribe en `DESIGN.md` §6.9.1b.

## Ronda B · Implementar la elegida en C

1. Porta el modo elegido a `stamp_band()` en `source/strip.c`. Usa `stamp_place()` del brief 01 y los mismos hashes que la versión en Python. Sin `float`. Cada `/` y `%` debe estar fuera de los bucles por píxel; aquí solo hay bucles por banda, así que se permiten.
2. Añade un test de host, `tests/test_strip_layout_parity.py`, que compile `source/strip.c` con `tests/host/strip_fake_kit.c`, o que lea un volcado si ya existe ese mecanismo; revisa `tests/test_strip.py`. El test comprueba, para la semilla `0xC0DE1234` y 64 bandas, que C y Python eligen las mismas estampas en las mismas posiciones. Comprueba también los corredores (≥48 px libres en las tres franjas) y la huella (≤15 %).
3. Ajusta los escenarios que dependen de la semilla fija: `cathedral_props_depth_collision` y `cathedral_bench_collision`. Si el prop ya no está en esas coordenadas, **no inventes otras**: avisa al coordinador. Él localiza el nuevo prop con un escenario de sondeo y una plantilla. La cobertura estable de colisión vive en `props_showcase_contacts`.

## Restricciones

- No cambies el baker de tiles ni los assets. El presupuesto de tiles no debe empeorar: la peor ventana debe seguir por debajo de 440.
- Las lápidas siguen siendo decoración: ni bloquean ni ocluyen.

## Criterio de aceptación

- El usuario aprueba la vista previa (ronda A) y luego la ROM (ronda B).
- Build sin warnings nuevos, tests de host PASS (incluido el de paridad) y `props_showcase_contacts` PASS.
- Capturas de 8 pantallas seguidas de la ROM con semilla fija en `walkthroughs/distribucion-catedral/assets/`.
