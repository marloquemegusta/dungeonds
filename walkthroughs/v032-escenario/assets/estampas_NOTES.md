# Diario de Iteraciones: Suelo por Estampas (Nintendo DS)

Worktree: `C:\codexlocal\dungeonds\.worktrees\v032-estampas` (rama `feat/v032-estampas`)
Pipeline: Blender 5.2 (geometría 3D de piezas) -> Lab headless Three.js (Playwright, 40.42 px/m, 16 rotaciones, alfa + sombra de contacto) -> Compositor de bandas (480x128) -> Medición de tiles hardware (BGR555, 8x8 deduplicados con volteo H/V/HV).

---

## Iteración s01 (Línea base mínima)

### Cambios realizados
- Implementada la biblioteca base de 4 piezas en 3D (`blender_pieces.py`, `make_pieces.py`):
  - `plank_whole_v1` (tablón entero con biseles y atlas de madera grimdark).
  - `panel_v1` (panel de 4 tablones con 2 travesaños y clavos).
  - `wire_coil_v1` (madeja de alambre de espino con barbas y espirales).
  - `puddle_1_v1` (charco turbio con borde húmedo y brillo especular).
- Creado el renderizador headless en el lab (`render_stamps.cjs`):
  - 16 rotaciones uniformes (paso 22.5°), cámara fija a 30° elevación, azimut 45°, escala exacta 40.42 px/m.
  - Corrección de escala: reseteo explícito de `state.mapGroup.scale` a 1:1 metros para evitar escalado automático.
  - Doble pasada para derivar alfa del objeto y sombra de contacto por diferencia sobre plano neutro receptor.
- Creado generador de fondo de barro simple (`mud_background.py`) a partir de 6 baldosas de 32x16 px extraídas de `albedo_tileable.png`.
- Creado el compositor de bandas (`compose_band.py`) y medidor de tiles (`count_tiles.py`).
- Generado carril completo de 6 pantallas (1152 px) y zoom 3x de 1 pantalla DS.

### Observación visual crítica (mirando s01_zoom_3x.png y s01_lane.png)
1. **Fondo de barro con costuras en rejilla**: Se aprecian líneas de corte rectangulares muy evidentes cada 32x16 px en el barro base. Las baldosas aleatorias no comparten bordes seamless, dando aspecto de mosaico de baldosas duras en vez de barro orgánico fluido.
2. **Pasarela continua pero rígida**: La pasarela conecta sin cortes entre bandas (cumple la regla de entrada/salida a x=240), pero al usar un único modelo de panel (`panel_v1`), el tramo recto parece una escalera repetitiva. Los giros entre tramos rectos y angulados son demasiado bruscos.
3. **Charcos tipo pegatina**: El charco actual tiene un reborde circular negro uniforme que parece una calcomanía superpuesta. Necesita bordes más desgastados e irregulares que se fundan con el barro.
4. **Alambre de espino y tablones**: Se leen a escala y tienen buen sombreado de contacto. Los personajes (esqueletos blancos, marine azul grisáceo) se recortan con excelente contraste sobre el fondo oscuro.
5. **Métricas de tiles**:
   - 1 banda (480x128): 219 tiles (grid 8px, 16 ángulos)
   - 3 bandas (480x384): 512 tiles
   - 6 pantallas (480x1152): 1300 tiles
   - Max ventana visible (33x25): **286 tiles** (Límite DS < 440: **PASS holgado**).

---

## Iteración s02 (Fondo continuo desplazado)

### Cambios realizados
- Reemplazo de las baldosas sueltas de 32x16 px por un fondo continuo reescalado directamente de `albedo_tileable.png` a 256x128 con cross-fade periódico en `mud_background.py`.
- Desplazamiento pseudoaleatorio `np.roll` por banda con semilla para variar la textura de fondo.
- Suavizado inicial de la curva senoidal de la pasarela central.

### Observación visual crítica (mirando s02_zoom_3x.png y s02_lane.png)
1. **Fondo visualmente perfecto**: Desaparecen al 100% las costuras rectangulares. El suelo se ve como un auténtico lodazal continuo y sombrío.
2. **Explosión del presupuesto de tiles (Defecto crítico)**:
   - Al desplazar píxel a píxel una textura de ruido de alta frecuencia (`(seed * 67) % tw`), cada celda de 8x8 px se convierte en un tile único no alineado.
   - 1 banda sube a **619 tiles**.
   - Max ventana visible sube a **815 tiles** (Fallo flagrante del hardware NDS: 815 > 440).
   - 6 pantallas alcanzan **4982 tiles**.
3. **Conclusión**: El fondo continuo con desplazamiento libre es inviable en NDS. Se requiere volver al enfoque de **baldosas modulares de 32x16 px**, pero diseñándolas con **márgenes de borde idénticos** (ventana de atenuación en bordes) para eliminar costuras y mantener el fondo en < 50 tiles.

---

## Iteración s03 (Baldosas sin costuras + Biblioteca 3D completa)

### Cambios realizados
- Implementado `mud_baldosas.py`: 6 baldosas de 32x16 px que comparten márgenes de borde idénticos mediante una ventana senoidal cúbica (`window = (wy * wx)**1.5`). Los bordes coinciden al 100% entre cualquier par de baldosas adyacentes.
- Modelado completo en Blender de las **23 piezas de la biblioteca** (`make_pieces.py`, `blender_pieces.py`):
  - Tablones: entero (`plank_whole_v1/v2`), agrietado (`plank_cracked_v1/v2`), roto (`plank_broken_v1/v2`).
  - Paneles de 4 tablones con travesaños (`panel_v1/v2`).
  - Alambre: madejas (`wire_coil_v1/v2`), serpenteante (`wire_zigzag_v1/v2`).
  - Charcos turbios con 3 formas (`puddle_1_v1`, `puddle_2_v1`, `puddle_3_v1`).
  - Escombros (`debris_pile_v1/v2`), huesos y casquillos (`bones_shells_v1/v2`), cantos (`stones_v1/v2`), jirones de tela burdeos (`rag_v1/v2`).
- Renderizado en el lab de las 23 piezas x 16 rotaciones (368 frames en total) y generación de `piece_library_sheet.png`.

### Observación visual crítica (mirando s03_zoom_3x.png y s03_lane.png)
1. **Éxito en fondo y tiles**: El fondo de baldosas con bordes idénticos se ve fluido y continuo (sin costuras) y el conteo de tiles cae a **215 tiles por banda** y **274 tiles en la ventana visible** (PASS holgado frente a 440).
2. **Riqueza ambiental**: La variedad de props (alambres sueltos, casquillos de latón, huesos blanquecinos, placas oxidadas y trapos burdeos) enriquece la narrativa sin saturar gracias a las zonas de calma de barro limpio.
3. **Defectos detectados**:
   - Los charcos tienen silueta excesivamente elíptica (demasiado geométrica).
   - Las transiciones de giro en la pasarela presentan quiebros angulares en los que las esquinas de los paneles sobresalen de forma algo dentada.

---

## Iteración s04 (Charcos orgánicos + Suavizado de curvatura + Arquitectura de Pool)

### Cambios realizados
- Re-modelado en Blender de los charcos (`build_puddle`): radio con armónicos de deformación orgánica (`0.14*sin(3a) + 0.09*sin(5a) + 0.05*sin(7a)`) y borde húmedo atenuado en valor para fundir mejor con el lodo.
- Re-renderizado de los charcos en el lab.
- En `compose_band.py`:
  - Limitada la variación angular entre paneles adyacentes a un máximo de 1 paso de rotación (22.5°), evitando quiebros bruscos.
  - Alternancia entre `panel_v1` y `panel_v2` e inserción de tablones sueltos/agrietados (`plank_cracked`, `plank_broken`).
  - Soporte de arquitectura de **pool de bandas** (`pool_size=3` y `pool_size=2`), emulando la selección por hash de bandas pre-horneadas del kit `strip_kit`.

### Observación visual crítica (mirando s04_zoom_3x.png y s04_lane.png)
1. **Charcos convincentes**: Ahora tienen contornos irregulares naturales de pozo de trinchera, con agua verdosa turbia y un punto de brillo solar especular coherente con la luz direccional.
2. **Pasarela orgánica tipo entarimado militar**: El camino serpentea de manera fluida, sin saltos en los vértices y manteniendo continuidad estricta de entrada y salida a x=240 px.
3. **Métricas de tiles**:
   - Con pool de 3 bandas (`pool3_grid8_16ang_shadow`): Total 6 pantallas = **508 tiles**, Max ventana = **295 tiles** (PASS).
   - Con pool de 2 bandas (`pool2_grid8_16ang_shadow`): Total 6 pantallas = **358 tiles**, Max ventana = **301 tiles** (PASS).
   - 1 banda individual: **195 - 200 tiles** (Cumple meta <= 300 tiles).

---

## Iteración s05 (Entrega final consolidada)

### Cambios realizados
- Consolidación de los activos definitivos:
  - `stamps_lane.png`: Carril completo de 512x1152 px (6 pantallas DS), muros laterales de 16 px, personajes de escala y recuadro de pantalla (256x192).
  - `stamps_lane_zoom_3x.png`: Ampliación 3x de la pantalla DS centrada sobre el marine y los esqueletos.
  - `piece_library_sheet.png`: Hoja de catálogo con las 23 piezas organizadas por categorías en 4 ángulos (0°, 45°, 90°, 135°).
- Ejecución completa de la matriz comparativa de políticas de tiles en `count_tiles.py`.

### Tabla Comparativa de Políticas de Presupuesto de Tiles (BGR555, 8x8 con volteo H/V/HV)

| Política / Configuración | 1 Banda (480x128) | 3 Bandas (480x384) | 6 Pantallas (480x1152) | Max Ventana Visible (33x25) | Límite VRAM (<440) | Meta Total (<=300) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Banda única periódica (pool=1, 16 ang, sombra)** | **211** | **211** | **211** | **204** | **PASS** | **CUMPLE (211 <= 300)** |
| **Pool 2 bandas (grid 8px, 8 ang, sombra)** | 200 | 356 | 356 | 297 | **PASS** | 356 (~56 sobre meta) |
| **Pool 2 bandas (grid 8px, 16 ang, sombra)** | 195 | 358 | 358 | 301 | **PASS** | 358 |
| **Pool 3 bandas (grid 8px, 8 ang, sombra)** | 200 | 500 | 500 | 290 | **PASS** | 500 |
| **Pool 3 bandas (grid 8px, 16 ang, sombra)** | 195 | 508 | 508 | 295 | **PASS** | 508 |
| 9 bandas libres (grid 8px, 8 ang, sin sombra) | 194 | 420 | 1144 | 252 | **PASS** | 1144 |
| 9 bandas libres (grid 8px, 8 ang, con sombra) | 204 | 447 | 1216 | 263 | **PASS** | 1216 |
| 9 bandas libres (grid 8px, 16 ang, con sombra) | 211 | 462 | 1233 | 271 | **PASS** | 1233 |
| 9 bandas libres (posición libre continua, 16 ang) | 215 | 472 | 1252 | 277 | **PASS** | 1252 |
