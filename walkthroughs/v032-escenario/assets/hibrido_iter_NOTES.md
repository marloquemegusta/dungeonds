# Iteraciones de Suelo Híbrido (floor_proc)

## v01 (Textura albedo_tileable.png + 8 baldosas en Y)
- **Cambios**:
  - Implementado `--mud-source image` (usando `albedo_tileable.png` preprocesado con `--mud-tone 0.75` y `--mud-desat 0.15`).
  - Fijado `proc_floor.py` para no sobreescribir `mud_texture` con ruido procedural cuando `mud-source == image`.
  - Ampliado el parche a 8 baldosas en Y (`--patch-tiles-y 8`, 6,336 m) y UVs calculados con repetición entera periódica para `--tex-span 3.168` (2 repeticiones en Y, 2 en X).
- **Qué vemos (análisis honesto)**:
  - El barro ahora tiene grano, relieve, piedras y mugre fotográfica real; el tono es mucho más oscuro y sombrío, eliminando la nube lisa beige rechazada.
  - Defecto grave: la pasarela modelada se confunde totalmente con los tablones ya pintados en la textura albedo del suelo (mismo valor y tono cálido).
  - Defecto de geometría: un tablón de la pasarela sobresale de forma anómala fuera del parche en la esquina superior izquierda debido a la duplicación periódica de objetos que cruzan el borde.
  - El alambre de espino en la esquina es demasiado fino, apagado y no se lee a 40 px/m.
- **Siguiente paso (v02)**:
  - Tablones modelados mucho más oscuros y fríos (paleta pizarra/carbón en el atlas, highlight frío en los biseles, tinte frío en el material).
  - Mayor altura y grosor de tablones (5,5 cm) y almohadillas de sombra de contacto bajo cada panel para generar oclusión ambiental en el barro.
  - Pasarela de 5 paneles con slotting sin desbordar el borde (elimina el tablón flotante): panel hundido en agua, panel con huecos, panel volcado/desplazado y ramal lateral corto.
  - Alambre de espino con bobinas grandes (50-75 cm), hilo de 3,6 cm, púas de 5,5 cm y contraste bimaterial (óxido naranja oscuro + brillos metálicos).
  - Agrupación de escombros en 3 focos narrativos y zonas de respiración sin piedras.

## v02 (Contraste de pasarela, alambre bimaterial y variedad narrativa)
- **Cambios**:
  - Paleta de madera del atlas oscurecida y enfriada a tonos pizarra/carbón `(27,29,32)`, biseles con highlight frío `(0.19,0.20,0.22)`.
  - Tablones más gruesos (5,5 cm) y elevados para arrojar sombras direccionales 3D.
  - Alambre de espino en bobinas grandes helicoidales de 50-75 cm, hilo de 3,6 cm, púas de 5,5 cm, con segmentos alternos de óxido naranja intenso y acero metálico reflectante (`metallic=0.78`).
  - Variedad de paneles: panel hundido, panel volcado, panel con huecos y ramal corto.
  - Focos de escombros y zonas de respiración limpias de piedras.
- **Qué vemos (análisis honesto)**:
  - El contraste visual de la pasarela es sobresaliente: los tablones modelados ahora se diferencian al instante de la mugre y tablones pintados del barro por su valor frío/oscuro y su relieve.
  - El alambre de espino se lee de inmediato como auténtica alambrada de trinchera con brillos metálicos espectaculares bajo la luz clave del lab.
  - Defecto crítico detectado en la imagen: dos artefactos fuera del parche:
    1) Una franja de tablón que sobresale en la esquina superior izquierda. Causa: `duplicate_edge_crossers` duplicó el panel 3 (volcado) que rozaba el borde superior hacia el vacío.
    2) Un polígono rectangular gris oscuro gigante en la esquina inferior derecha. Causa: la almohadilla de sombra de contacto del panel 0 rozaba el borde inferior y fue duplicada a coordenadas fuera de límite.
## v03 (Corrección de desbordamientos, panel central volcado y charcos reflectantes)
- **Cambios**:
  - Excluidos explícitamente elementos de la pasarela y alambrada de `duplicate_edge_crossers`.
  - Pasarela estructurada en 5 paneles estrictos de 1,06 m dentro de slots de 1,267 m:
    - Panel 0: entrada sólida dentro de márgenes.
    - Panel 1: panel hundido en el barro y agua.
    - Panel 2: panel volcado y desplazado en el centro del parche (lejos de los bordes).
    - Panel 3: panel con huecos centrales.
    - Panel 4: salida sólida dentro de márgenes.
  - Almohadillas de sombra de contacto ajustadas a solo +2 cm de margen con tono sombra húmeda.
  - Mayor reflectividad en charcos de agua turbia (roughness 0.22, brillo metálico 0.35) y cabezas de clavos con glint metálico.
- **Qué vemos (análisis honesto)**:
  - Los artefactos fuera de borde han desaparecido por completo: ni tablón flotante en la esquina superior izquierda ni rectángulo negro en la inferior derecha.
  - La pasarela es legible al instante, oscura y fría, con volumen real y ritmo narrativo excelente (panel hundido, panel volcado en el centro, huecos y ramal lateral).
  - El alambre de espino se lee como madejas grandes con púas visibles y brillos de acero oxidado.
  - Los escombros están bien agrupados y las zonas de barro liso respiran con naturalidad.
- **Siguiente paso (v04)**:
  - Ejecutar verificación de periodicidad dura (`--tile-check y`), que duplica el parche 1x2 a lo largo del eje Y en el lab para auditar la costura de unión central.

## v04 (Verificación de periodicidad --tile-check y / Versión Final Entregada)
- **Cambios**:
  - Ajuste en `tools/floor/iterate_render.py` para optimizar el render headless del tile-check 1x2 (resolución de 320 px y `waitTexturesMs=4000`), evitando timeouts de SwiftShader bajo carga de 960k triángulos.
  - Ejecución del pase completo con `--tile-check y`.
- **Qué vemos (análisis honesto de la unión)**:
  - En `assets/models/environment/floor_proc/iter/v04_tilecheck_lab3x.png`, la costura central entre el parche 1 y el parche 2 es 100% continua e invisible:
    - La pasarela mantiene un espaciado idéntico (~18 cm) entre el panel 4 y el panel 0 repetido, sin cortes ni saltos geométricos.
    - La textura del barro (`albedo_tileable.png`) con repetición entera de 2.0x en X y 2.0x en Y encaja a la perfección sin líneas de costura ni cambios de tono.
    - El relieve de altura procedural y los charcos transicionan sin discontinuidades gracias a las funciones senoidales periódicas cerradas.
  - Criterios de aceptación cumplidos en su totalidad. **v04 es la versión definitiva entregada en `floor_proc_patch.glb`**.

