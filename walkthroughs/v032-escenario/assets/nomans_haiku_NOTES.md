# Tierra de Nadie: notas de iteracion (agente Haiku)

Escala unica: 17,9 px/m. Cifras de tiles: `lane/tile_budget.json`.

## Calibracion de escala

- Pieza `calib_pole_2m` (poste de 2 m, Cycles, camara ortografica 30 grados de elevacion y 45 de azimut).
  Altura medida en el sprite de giro 0: **30 px** (alfa > 128); esperado 2 m x cos 30 x 17,9 = **31,0 px**.
  Marine de referencia (`assets/sprites/characters/marine/frames/4_N/0.png`): 31 px de alto.
- La varilla horizontal de 2 m (`calib_rod_x_2m`) se midio solo con el lab; no se ha vuelto a medir en Blender.

## Que NO se uso: render del lab (FBX-Web-Renderer)

Primer intento: `render_stamps.cjs` adaptado al lab (Playwright headless). La varilla de 2 m salia de 18 px
y el poste de 2 m de 18 px, es decir, la mitad de lo esperado, y el origen aparecia desplazado. Se probo
un multiplicador de frustum (x2) sin conseguir proporciones coherentes entre eje vertical y horizontal.
En lugar de seguir depurando el lab, los sprites y las baldosas se renderizan en Blender (Cycles, CPU, 48
muestras, camara ortografica exacta). Las mediciones de la escala salen de la geometria, no de un ajuste.
El lab queda sin uso en este worktree; no se ha tocado `tools/lab/`.

## Iteraciones

- **n01**: calibracion (poste 2 m), baldosas, 1 crater y 1 alambrada.
  Cambio: primer render en lab, descartado (ver arriba); pasa a Blender.
  Veo: el crater con borde transparente radial se lee como crater; las alambradas, con 1 px de hilo, se leen
  como alambre. Defecto: el anillo interior del crater hacia dientes de sierra (frontera de material por cara).
- **n02**: biblioteca completa (24 piezas) y hoja `library/piece_library_sheet.png`.
  Veo: craters y restos legibles; sacos, casquillos y charcos, a 1-3 px, casi ilegibles a escala real (esperable).
  Defecto: craters con ejecta demasiado clara (se ve como plato).
- **n03**: baldosas corregidas. Las variantes usaban desplazamientos distintos de la textura: las aristas no
  casaban (costura) y el mosaico parecia un tablero. Ahora todas comparten textura periodica y solo cambia
  el tono con modulacion periodica. Pool de 7 bandas: se ve sin tablero.
  Crater: material oscurecido. Piezas que no entraban en la banda (sombra difusa ocupaba todo el canvas) ahora
  se miden con alfa > 40.
- **n04**: estampas con esquina en multiplo de 8 px (fase de la rejilla de tiles). Sin efecto grande en tiles.
  Medicion: suelo solo = 64 tiles por banda; con estampas, 531.
- **n05**: medicion de palancas. Rotacion de 16 a 4 giros: sin efecto apreciable (516 vs 531 tiles).
  Alfa de 1 bit (como exige el DS en sprites): baja de 2760 a 2299 tiles en el pool de 7 bandas.
  Se deja alfa de 1 bit por defecto.
- **n06**: carril de 6 pantallas y zoom 3x generados. Veo: la tanqueta y los craters dominan y la escala
  de esqueletos (37 px) y marine es creible. Defecto: la trinchera se lee como una banda plana con sacos en
  los bordes; los tablones no se distinguen.
- **n07**: no hecha (ver "No hecho").

## Tiles (ultima medicion, `python tools/stamps/nomans_compose.py tiles`)

| Medida | Valor | Objetivo |
| --- | --- | --- |
| 1 banda | 441 | - |
| 3 bandas | 901 | - |
| 7 bandas (pool) | **2299** | <= 400 |
| Peor ventana 33x25 | **495** | <= 300 (tope 440) |

Causas medidas: suelo solo 64 por banda. Las estampas con alfa (sombra y ejecta) sobre suelo variable
generan celdas distintas por posicion. Palancas no aplicadas: menos piezas (reducir variantes), sombra de
contacto sin degradado, bordes mas duros en el suelo bajo estampas, o restringir la paleta del suelo.

## No hecho

- Escena de referencia 3D de una banda: no hecha.
- Huellas de colision en JSON: no hechas.
- Variantes por semilla (2-3 por pieza): no hechas; hay una semilla por pieza.
- Craters de 8 m: casi nunca caben en la banda de 128 px (el colocador descarta la mayoria).
- Trinchera: los tablones no se ven; no se ha iterado.
