# Prompts de piezas para Tripo: la catedral

Imágenes de **una pieza suelta** para convertir a 3D con Tripo (mismo flujo que los personajes). Después se prerenderizan en el lab y de esos prerenders sale la paleta.

## Pasos

1. En Gemini, pega el **bloque común** y la línea de **`banco_intacto`**. Repite hasta que te guste: será la **referencia de estilo** del resto.
2. Para cada otra pieza, **adjunta la imagen del banco** y pega el bloque común y la línea de la pieza. Una pieza por generación.
3. Guarda cada imagen en `props/<nombre>.png`.
4. Pásala por Tripo y guarda el modelo con el mismo nombre en `props/`.

## Bloque común (pegar siempre)

```
Single isolated game asset for a 3D conversion (image-to-3D). One object only, fully visible, centered, nothing cut off. Plain flat light-grey background, no floor, no shadow, no other objects, no text. Three-quarter view from slightly above, even soft studio lighting, no strong highlights. Gothic Catholic grimdark style (Warhammer 40k, Trench Crusade, Blasphemous): dark warm stone, aged wood, tarnished bronze and gold, bone, deep burgundy. Realistic proportions, clean readable shapes. If a reference image is attached, match its style, materials and colors exactly.
```

## Piezas (lote 1)

| Archivo | Línea de la pieza |
|---|---|
| `banco_intacto` | A long wooden church pew, carved gothic ends, intact and polished. |
| `banco_roto` | The same wooden church pew, broken in the middle, splintered, scorched. |
| `banco_volcado` | The same wooden church pew lying overturned on its back. |
| `columna` | Base and lower part of a clustered gothic stone pillar, cracked, soot-stained. |
| `santo` | Stone statue of a warrior saint holding a sword, on a plinth, weathered. |
| `relicario` | Gilded gothic reliquary chest with small spires, on a short stone altar. |
| `sacos` | Short wall of stacked sandbags topped with barbed wire on wooden posts. |
| `vela` | Cluster of three tall church candles on a puddle of melted wax, unlit. |

La vela va **apagada**: la llama la anima el juego.

## Lote 2: lápidas del suelo

Piezas **planas** que el juego pone a ras de suelo (no son obstáculo). En Tripo se modela **la losa suelta**, sin suelo alrededor. Mismo bloque común, adjuntando la imagen del banco como referencia, y en vez de "Three-quarter view from slightly above" la vista va casi cenital para que Tripo vea bien el grabado.

| Archivo | Línea de la pieza |
|---|---|
| `lapida_cruz` | A single loose flat rectangular stone tomb slab lying on nothing, isolated object, about 2 m by 1 m and 15 cm thick, all four edges and the thickness visible, worn and cracked, a large carved Latin cross with a sword along it, faded engraved border, no text. Seen from above at a steep angle. |
| `lapida_caballero` | A single loose flat stone tomb slab of a crusader knight lying on nothing, isolated object, about 2 m by 1 m and 15 cm thick, all four edges and the thickness visible, shallow carved relief of a knight lying with hands joined in prayer over a long sword, a small shield at his feet, worn smooth and cracked, a corner chipped off. Seen from above at a steep angle. |

## Lote 3: losas del suelo (damero de rombos)

Cada imagen es **una sola losa cuadrada suelta** (1,26 m de lado, ~8 cm de grosor). Un script las gira 45°, las recorta para que encajen y las coloca en damero; las juntas pueden quedar con alguna grietilla sobre un fondo gris oscuro. Mismo bloque común con la imagen del banco como referencia, quitando "Three-quarter view from slightly above". Las dos piedras del damero deben ser **casi del mismo tono** (poco contraste).

| Archivo | Línea de la pieza |
|---|---|
| `losa_a` | A single loose square floor slab of dark warm grey-brown limestone, 1.26 m by 1.26 m and 8 cm thick, all four edges and the thickness visible, worn smooth by centuries of footsteps, slightly bevelled edges, subtle shallow pits, very low contrast surface. Seen from above at a steep angle. |
| `losa_b` | The same square floor slab in a slightly cooler and slightly darker grey stone, same size and wear, very low contrast surface. Seen from above at a steep angle. |
| `losa_grieta` | The same square dark limestone floor slab with one long thin crack across it and a small chipped corner, otherwise worn smooth. Seen from above at a steep angle. |
| `losa_rota` | The same square dark limestone floor slab broken into three or four pieces that are still in place, slightly uneven, thin dark gaps between pieces. Seen from above at a steep angle. |
| `losa_cera` | The same square dark limestone floor slab with old dried candle wax drips and a faint dark stain, worn. Seen from above at a steep angle. |
| `losa_sangre` | The same square dark limestone floor slab with an old dried dark-red bloodstain soaked into the stone and a few scuff marks. Seen from above at a steep angle. |
