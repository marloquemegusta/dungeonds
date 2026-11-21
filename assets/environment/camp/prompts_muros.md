# Kit de muros del campamento (prompts para generar las imágenes)

Objetivo: tres piezas del MISMO estilo que se ensamblan en Blender con la misma escala y el mismo grosor:
laterales y trasera = panel liso repetido; entrada = panel con portón; unión = contrafuerte de esquina.
Decisión de diseño: `DESIGN.md` §7.5 («Entrada de la catedral en un muro de módulos»).

## Bloque de estilo (se pega al final de los tres prompts, sin cambiar nada)

```
Same stone and same style for the whole set. Weathered grey-brown limestone, ruined medieval Gothic courtyard
wall, subtle moss in the cracks, some chipped edges, no ivy, no text, no people. Painterly but realistic
texture, flat neutral studio lighting with no cast shadows and no strong highlights, so it can be relit later.
Straight-on orthographic FRONT view, no perspective, no tilt, centred, whole piece visible, plain solid
light-grey background, nothing else in the image. Muted desaturated palette.
```

## 1. Panel liso (laterales y trasera)

```
A single straight stone wall panel, a rectangular slab of ruined Gothic masonry, proportions 2 wide by 3 tall,
about 0.3 thick. Large cut blocks in regular courses. A shallow blind pointed-arch niche carved in the
centre of the face. The left and right edges are flat, vertical and unadorned so that identical panels can be
placed side by side without a visible seam. Flat top edge with a simple stone cap.
```

## 2. Panel con portón (la entrada)

```
Exactly the same wall panel as the plain one (same stone, same blocks, same proportions 2 wide by 3 tall,
same thickness, same top cap, same flat vertical side edges), but with a tall pointed Gothic doorway cut
through the centre: opening about 45% of the panel width and 70% of its height, starting at the bottom edge,
with a moulded arch frame and a dark empty interior (the door opening is black). No door leaf, no steps.
```

## 3. Contrafuerte de esquina

```
A tall square stone buttress pillar of the same ruined Gothic limestone, same blocks and same style as the
wall panels. Height exactly the same as the wall panels, width about one quarter of a panel width, a little
thicker than the panels (about 0.4), with a small chamfered stone cap on top and a plain plinth at the base.
Its left and right faces are flat so wall panels can butt against it.
```

## Qué comprobaré cuando lleguen las imágenes
- Misma piedra, color y escala de bloques en las tres.
- Misma altura y proporción 2:3 en los paneles; el portón ocupa ~45 % de ancho y ~70 % de alto.
- Bordes laterales planos y verticales, sin adornos que impidan unir paneles.
- Vista frontal sin perspectiva, sin sombras proyectadas, fondo liso.
- El contrafuerte tiene la misma altura que los paneles.

Después: 3D (Tripo) → ensamblaje en Blender → render en el laboratorio con luz de luna → ROM.
