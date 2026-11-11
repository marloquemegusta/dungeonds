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

## Lote 4: muros y vidrieras

La primera pasada de la vidriera y su paleta quedó autorizada el 2026-11-09: el modelo Blender está en `assets/models/environment/cathedral/lancet_pair.blend`; la ROM usa una rasterización provisional del perfil geminado con piedra gris cálida, plomo oscuro, burdeos, azul-violeta y oro apagado. Estos briefs describen las siguientes variantes de producción, revisables con el usuario. Las medidas en píxeles describen el **prerender ortográfico**, no el tamaño de la malla ni una huella de colisión.

| Archivo | Línea de la pieza |
|---|---|
| `pano_muro_modular` | One isolated, repeatable interior side-wall bay for a dark Gothic cathedral, viewed from inside the nave. A shallow pointed blind arcade between clustered stone pilasters, with a continuous low plinth and matching upper moulding. Its longitudinal span should occupy 128 pixels in the canonical game render. No window, statue, furniture or floor. Both ends must join cleanly to an identical neighboring bay without a visible seam. Keep all floor-level geometry within the outer 48-pixel wall strip in the canonical game render; nothing may project into the walkable nave. Weathered warm-grey limestone, restrained cracks and soot, broad readable stone shapes, low-contrast wall surface. Show the complete module on a plain light-grey background, no cast shadow, no people, no text. Height and final screen scale will be judged beside the 2 m marine in the canonical orthographic render; avoid tiny tracery. |
| `lanceta_geminada` | One isolated Gothic Catholic paired-lancet stained-glass insert for a vertical side wall. Two narrow pointed openings separated by a carved stone mullion, with a stone frame mounted flush into a separate wall bay. The opening should occupy about 32 by 48 pixels in the canonical orthographic game render. Keep the frame silhouette regular for a broken-glass variant. First-pass palette: deep burgundy, blue-violet and muted old gold with dark lead. Show the complete insert from the interior side, slightly above. No full wall segment, floor, cast shadow, light beam or text. Readable at Nintendo DS resolution; avoid tiny filigree. |
| `roseton_arco` | One isolated circular Gothic Catholic rose window for the front face of a cathedral transept arch. The opening should occupy about 64 by 64 pixels in the canonical orthographic game render. Twelve clear radial stained-glass sectors, dark lead lines, thick weathered limestone tracery and a pointed stone surround integrated into a short arch panel. Use the user-approved tracery reference and glass palette. Show it straight-on from the nave, centered and fully visible. No room, floor, people, light beam or text. Strong readable shapes at Nintendo DS resolution; no hairline ornament. |
| `contrafuerte` | One isolated narrow Gothic Catholic stone wall buttress / clustered pilaster for a dark cathedral interior. A strong base, clustered shafts and a simple pointed capital; weathered warm-grey limestone, soot in the joints and a few chipped edges. At floor level it must fit inside the outer 48-pixel side-wall strip in the canonical game render, with no base projection into the walkable nave. Three-quarter interior view, full object visible. No wall, floor, shadow, people or text. Readable silhouette at Nintendo DS resolution; avoid delicate decoration. |

**Variante vertical de `pano_muro_modular` (decidida 2026-11-11, pendiente de confirmar la orientación en `DESIGN.md`):** cada módulo mide unos 48 × 128 px en vertical (1 : 2,7), con el arco apuntado de pie, zócalo abajo y moldura arriba en los bordes de la imagen y medio pilar cortado por el centro a cada lado, para apilar en vertical y repetir sin costura. Texto para Gemini (adjuntar el banco como referencia de estilo):

```
Redo this exact stone wall bay with a different shape: a tall, narrow PORTRAIT module, about 1 unit wide by 2.7 units tall (for example 480 x 1280 px), instead of the wide landscape one. Keep the same material, colour, soot stains, chipped edges, stone coursing and depth of relief. Straight-on orthographic front elevation, no perspective, perfectly symmetrical left to right. One single tall pointed Gothic arch, recessed with a moulded surround, filling almost the whole width and rising most of the height, with its point toward the top of the image. Below the arch: a continuous low stone plinth across the full width. Above the arch: a continuous horizontal stone moulding across the full width. The plinth and the moulding must be at the very bottom and the very top edge of the image, so that copies stacked one on top of the other form a continuous wall. Left and right edges: only HALF of a clustered pilaster on each side, cut exactly through the centre of the pilaster, with no capital or base sticking out beyond the edge, so that two copies placed side by side would join with no visible seam. The left edge and the right edge must be mirror images of each other. Flat back, shallow relief, nothing projecting forward. No window glass, no statue, no floor, no people, no text. Even soft light, plain light-grey background, no cast shadow. Broad readable stone shapes, no tiny tracery.
```

Antes de enviarla a Tripo, pegar dos copias una encima de la otra y otra al lado en un editor de imágenes: no debe verse costura en ninguna de las dos pruebas.
