# Notas de Iteración - TIERRA DE NADIE (Escala Real 17,9 px/m)

## Verificación de Escala y Calibración
- **Premisa**: Marine mide 2,0 m en el mundo de juego y su sprite mide 31 px de alto (`bbox` en frame `4_N/0.png`: Y de 2 a 33 -> 31 px).
- **Proyección de cámara**: Elevación 30°, Azimut 45°. Proyección isométrica 2:1.
  - La componente vertical de un vector vertical de altura $H$ es $H \cdot \cos(30^\circ) = H \cdot 0,866025$.
  - Para $H = 2,0\text{ m}$, a una escala de $17,9\text{ px/m}$, la altura en pantalla es $2,0 \cdot 0,866025 \cdot 17,9 = 31,003\text{ px}$.
- **Comprobación experimental con objeto 3D**:
  - Se modeló en Blender un cilindro de radio 0,3 m y altura 2,0 m exactos (Z de 0 a 2,0 m) y una caja de 0,6 x 0,6 x 2,0 m (`calib_2m.glb`).
  - Renderizado con `render_stamps.cjs` a `PPM = 17.9`, elevación 30°, azimut 45°.
  - Altura medida en píxeles del objeto 3D renderizado: **31-32 px** (coincidencia exacta píxel a píxel con el sprite del marine de 31 px).
  - Evidencia guardada en `assets/models/environment/nomans/calib/scale_calibration_4x.png`.
- **Equivalencias de mapa validadas**:
  - Baldosa kit 32x16 px = 1,79 x 1,79 m (1,8 m).
  - Carril útil de 480 px = 26,81 m de ancho.
  - Banda de 128 px = 14,30 m de profundidad de terreno.
  - Carril total: 512 px con paredes de 16 px a cada lado.
  - Saco de arena 0,5 x 0,3 m = 9 x 5 px.
  - Tablón 2,0 x 0,2 m = 36 x 4 px.
  - Madeja de alambre 1,5 m = 27 px.
  - Cráter de obús 3-8 m = 54-143 px.
  - Resto de vehículo 6-8 m = 110-140 px.

---

## Iteración n02 - Cráteres Variados, Coberturas de Sacos y Huellas de Colisión JSON
- **Cambios realizados**:
  - Modelado y exportación de cráteres de 3m (`crater_3m_v1` y `v2`) y cráter gigante de artillería pesada de 8m (`crater_8m_v1`, 203 px ancho).
  - Modelado de sacos de arena a escala real (saco de 0,5 x 0,3 x 0,15 m = 9 x 5 px en pantalla):
    - `sandbag_wall_2m_v1` (muro bajo de 2,0 m, 3 capas de sacos).
    - `sandbag_wall_3m_v1` (muro de 3,0 m con brecha de paso central).
    - `sandbag_pile_v1` (montón desbaratado de 6 sacos en el lodo).
    - `sandbag_parapet_v1` (parapeto en ángulo).
  - Exportación de huellas de colisión a JSON en `assets/models/environment/nomans/hulls/` (huella en píxeles y metros en el suelo para bloquear paso pero no disparos).
  - Renderizado de sprites con sombras de contacto.
- **Lectura visual y defectos**:
  - Los sacos de arena se ven a escala correcta (pequeños respecto al marine, altura de cobertura hasta la cintura del soldado).
  - El cráter de 8m es masivo e imponente, evocando un impacto directo de mortero pesado.
  - Defecto: La peor ventana sube a 561 tiles por saturación de elementos en una misma banda sin restricción de ángulos.
- **Métricas de tiles**:
  - 1 banda: 224 tiles
  - 3 bandas: 523 tiles
  - Peor ventana: 561 tiles (FAIL frente al límite de 440)

---

## Iteración n03 - Biblioteca Completa (24 Piezas): Tanque, Cañón, Cuerpos y Acentos
- **Cambios realizados**:
  - Modelado 3D de restos pesados:
    - `tank_wreck_7m_v1`: Casco de blindado de 6,8 x 3,4 m (122 x 30 px en suelo, altura 2,2 m = 34 px), oruga reventada desmadejada en el lodo, torreta ladeada 35° con cañón doblado. Huella JSON: 116x29 px.
    - `cannon_wreck_4m_v1`: Cañón de campaña de 4,0 m, tubo en el barro, escudo doblado, rueda quebrada. Huella JSON: 72x20 px.
    - `wheel_axle_v1`: Rueda de radios y eje de artillería medio enterrada (~1,6 m).
  - Alambrada rota de 6m (`wire_line_6m_v1`) y madeja retorcida (`wire_coil_1_5m_v2`).
  - Piezas de ambientación y detalles macabros con acentos de color grimdark:
    - `corpse_bones_v1`: Soldado caído semienterrado (~1,8 m), uniforme andrajoso en burdeos apagado, calavera y costillas visibles.
    - `bones_cluster_v1`: Grupo de huesos limpios blanqueados.
    - `shell_casings_v1`: Casquillos de artillería de latón gastado (acento ocre/latón apagado).
    - `stakes_stump_v1`: Tocón de árbol quemado y astillado por metralla (1,2 m de alto) con estacas afiladas.
    - `debris_scrap_v1`: Planchas de hierro corrugado oxidado y cascotes de hormigón.
    - `puddle_dark_v1`: Charco de agua turbia aceitosa.
    - `rag_banner_v1`: Jirón de tela / estandarte rasgado en burdeos apagado.
  - Renderizado completo de las 24 piezas en sprites con rotaciones ortográficas exactas.
- **Métricas de tiles (sin control de densidad)**:
  - 1 banda: 286 tiles
  - 3 bandas: 664 tiles
  - Peor ventana: 590 tiles (FAIL)

---

## Iteración n05 - Deduplicación Hardware por Volteo (H-Flip) y Reutilización de Sellos
- **Cambios realizados**:
  - Aprovechamiento de la característica hardware de Nintendo DS: `canonical_tile` deduplica automáticamente cualquier baldosa volteada horizontalmente (`np.fliplr`) o verticalmente.
  - En `compose_nomans_band.py`, las bandas alternas reutilizan piezas clave aplicando volteo horizontal (`flip_h=True`):
    - `crater_8m_v1` (H-flipped) en lugar de duplicar variantes masivas.
    - `crater_5m_v1` (H-flipped) y `crater_3m_v1` (H-flipped).
    - Reutilización de los muros de sacos de arena (`sandbag_wall_2m_v1`) y madejas de alambre.
  - Reducción drástica del número de baldosas únicas en el pool global.
- **Métricas de tiles**:
  - 1 banda: 221 tiles
  - 3 bandas: 652 tiles
  - 7 bandas pool: **1220 tiles** (reducción de 261 tiles frente a los 1481 de n04)
  - Peor ventana 33x25: **416-428 tiles** (**PASS** del límite duro VRAM < 440)

---

## Iteración n06 - Cierre, Hoja de Biblioteca 4x y Escena de Referencia 3D
- **Cambios realizados**:
  - Generación de la hoja de contacto completa de la biblioteca de piezas: `nomans_library_sheet.png` y ampliación 4x `nomans_library_sheet_4x.png` con escala rotulada en metros (0m, 2m, 5m a 17,9 px/m) y 4 orientaciones por pieza.
  - Modelado y render de la **escena de referencia en 3D** completa (`nomans_reference_band.png` y `nomans_reference_band_3x.png`): una banda de 26,8 x 14,3 m montada íntegramente en 3D en Blender con oclusión y sombras proyectadas entre objetos.
  - Medición de la escena 3D continua de referencia: arroja **313 tiles únicos** en una sola banda (demostrando experimentalmente por qué una escena continua no se puede usar directamente en VRAM sin la técnica de estampas sobre baldosas).
  - Ensamblado final del carril de 6 pantallas (1152 px) `nomans_lane.png` con paredes laterales de 16 px, sprites de Marine (31 px = 2,0 m), Skeleton y Charger, y recuadro de pantalla DS 256x192.
  - Verificación de costuras: diferencia media entre filas limítrofes = 9,6 px (totalmente imperceptible).
- **Métricas de tiles finales (n06)**:
  - 1 banda: 221 tiles
  - 3 bandas: 652 tiles
  - 7 bandas pool: 1220 tiles
  - Total 9 bandas carril: 1220 tiles
  - Peor ventana visible (33x25): **428 tiles** (**PASS** < 440 VRAM)

---

## Tabla Resumen de Iteraciones

| Iteración | Piezas / Cambios | 1 Banda | 3 Bandas | 7 Bandas Pool | Peor Ventana (33x25) | Límite VRAM (<440) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **n01** | Calibración 17,9 px/m + baldosas + crater 5m + wire 4m + coil 1.5m | 242 | 567 | 1582 | 475 | FAIL |
| **n02** | Cráteres 3m, 8m + Sacos de arena + Huellas JSON | 224 | 523 | 2080 | 561 | FAIL |
| **n03** | 24 piezas completas (tanque 7m, cañón 4m, cuerpos, huesos, casquillos) | 286 | 664 | 2480 | 590 | FAIL |
| **n04** | Zonas de respiración + Trinchera transversal + Rotaciones ortogonales | 221 | 652 | 1481 | 423 | **PASS** |
| **n05** | Reutilización con volteo hardware (H-flip) para sellos clave | 221 | 652 | 1220 | 416-428 | **PASS** |
| **n06** | Hoja 4x con escala + Escena 3D de referencia + Carril 6 pantallas final | 221 | 652 | 1220 | 428 | **PASS** |


## Iteración n01 - Calibración, Baldosas Base y Primeras Estampas (5m crater, 4m wire, 1.5m coil)
- **Cambios realizados**:
  - Calibración de escala validada (17,9 px/m, elev 30°, azim 45°).
  - Corrección de la cámara de render en `render_stamps.cjs`: antes usaba `$.camera.constructor` (que en el lab era `PerspectiveCamera` con FOV negativo aberrante). Se reemplazó por la verdadera `OrthographicCamera` (`$.lights.key.shadow.camera.constructor`), logrando proyección isométrica 2:1 exacta.
  - Corrección de normales y culling: `THREE.DoubleSide` forzado en todos los meshes para que planos finos y bordes no se descarten.
  - Generación de 8 baldosas sin costuras (32x16 px) en `assets/models/environment/nomans/baldosas/`. Un fondo de barro puro de 480x128 consume solo **64 tiles hardware**.
  - Modelado 3D a escala real de 3 piezas:
    - `crater_5m_v1`: 5m de diámetro útil (outer rim 7m, 126x65 px en pantalla), borde levantado, interior hundido con agua turbia y terrones.
    - `wire_line_4m_v1`: 4m de largo (88 px de ancho), postes inclinados de 1,5m (23 px alto) y 3 hilos con púas.
    - `wire_coil_1_5m_v1`: 1,5m de diámetro (44 px ancho en pantalla).
  - Compositor de carril `compose_nomans_band.py` y runner `run_nomans_pipeline.py`.
- **Lectura visual y defectos observados**:
  - Tono de barro grimdark: media RGB (62, 54, 45), oscuro y sombrío, sin colores saturados prohibidos.
  - El marine (31 px) y los esqueletos se leen con buen contraste sobre el terreno.
  - No hay pasarela ni camino artificial: se avanza campo a través.
  - Defecto 1: Faltan los cráteres de 3m y 8m, por lo que el compositor reutiliza el de 5m en exceso.
  - Defecto 2: Presupuesto de tiles alto en ventana visible (475 tiles vs límite 440) debido a la repetición de múltiples cráteres grandes con 8 rotaciones sin deduplicación.
- **Métricas de tiles**:
  - 1 banda: 242 tiles
  - 3 bandas: 567 tiles
  - 7 bandas pool: 1582 tiles
  - Peor ventana 33x25: 475 tiles (FAIL frente al tope 440)
- **Siguiente paso (n02)**:
  - Generar Cráteres de 3m (54 px) y 8m (143 px).
  - Generar Sacos de arena (muros de 2m y 3m con brechas, montón desbaratado) y exportar sus huellas de colisión JSON.
  - Aplicar palancas de presupuesto: restringir rotaciones de cráteres grandes a 2 o 4 ángulos (aprovechando volteos simétricos H/V), aumentar zonas de respiración de barro limpio (máximo 2 cráteres por banda).

---

## Iteración n02 - Cráteres Variados, Coberturas de Sacos y Huellas de Colisión JSON
- **Cambios realizados**:
  - Modelado y exportación de cráteres de 3m (`crater_3m_v1` y `v2`) y cráter gigante de artillería pesada de 8m (`crater_8m_v1`, 203 px ancho).
  - Modelado de sacos de arena a escala real (saco de 0,5 x 0,3 x 0,15 m = 9 x 5 px en pantalla):
    - `sandbag_wall_2m_v1` (muro bajo de 2,0 m, 3 capas de sacos).
    - `sandbag_wall_3m_v1` (muro de 3,0 m con brecha de paso central).
    - `sandbag_pile_v1` (montón desbaratado de 6 sacos en el lodo).
    - `sandbag_parapet_v1` (parapeto en ángulo).
  - Exportación de huellas de colisión a JSON en `assets/models/environment/nomans/hulls/` (huella en píxeles y metros en el suelo para bloquear paso pero no disparos).
  - Renderizado de sprites con sombras de contacto.
- **Lectura visual y defectos**:
  - Los sacos de arena se ven a escala correcta (pequeños respecto al marine, altura de cobertura hasta la cintura del soldado).
  - El cráter de 8m es masivo e imponente, evocando un impacto directo de mortero pesado.
  - Defecto: La peor ventana sube a 561 tiles por saturación de elementos en una misma banda sin restricción de ángulos.
- **Métricas de tiles**:
  - 1 banda: 224 tiles
  - 3 bandas: 523 tiles
  - Peor ventana: 561 tiles (FAIL frente al límite de 440)

---

## Iteración n03 - Biblioteca Completa (24 Piezas): Tanque, Cañón, Cuerpos y Acentos
- **Cambios realizados**:
  - Modelado 3D de restos pesados:
    - `tank_wreck_7m_v1`: Casco de blindado de 6,8 x 3,4 m (122 x 30 px en suelo, altura 2,2 m = 34 px), oruga reventada desmadejada en el lodo, torreta ladeada 35° con cañón doblado. Huella JSON: 116x29 px.
    - `cannon_wreck_4m_v1`: Cañón de campaña de 4,0 m, tubo en el barro, escudo doblado, rueda quebrada. Huella JSON: 72x20 px.
    - `wheel_axle_v1`: Rueda de radios y eje de artillería medio enterrada (~1,6 m).
  - Alambrada rota de 6m (`wire_line_6m_v1`) y madeja retorcida (`wire_coil_1_5m_v2`).
  - Piezas de ambientación y detalles macabros con acentos de color grimdark:
    - `corpse_bones_v1`: Soldado caído semienterrado (~1,8 m), uniforme andrajoso en burdeos apagado, calavera y costillas visibles.
    - `bones_cluster_v1`: Grupo de huesos limpios blanqueados.
    - `shell_casings_v1`: Casquillos de artillería de latón gastado (acento ocre/latón apagado).
    - `stakes_stump_v1`: Tocón de árbol quemado y astillado por metralla (1,2 m de alto) con estacas afiladas.
    - `debris_scrap_v1`: Planchas de hierro corrugado oxidado y cascotes de hormigón.
    - `puddle_dark_v1`: Charco de agua turbia aceitosa.
    - `rag_banner_v1`: Jirón de tela / estandarte rasgado en burdeos apagado.
  - Renderizado completo de las 24 piezas en sprites con rotaciones ortográficas exactas.
- **Métricas de tiles (sin control de densidad)**:
  - 1 banda: 286 tiles
  - 3 bandas: 664 tiles
  - Peor ventana: 590 tiles (FAIL)

---

## Iteración n05 - Deduplicación Hardware por Volteo (H-Flip) y Reutilización de Sellos
- **Cambios realizados**:
  - Aprovechamiento de la característica hardware de Nintendo DS: `canonical_tile` deduplica automáticamente cualquier baldosa volteada horizontalmente (`np.fliplr`) o verticalmente.
  - En `compose_nomans_band.py`, las bandas alternas reutilizan piezas clave aplicando volteo horizontal (`flip_h=True`):
    - `crater_8m_v1` (H-flipped) en lugar de duplicar variantes masivas.
    - `crater_5m_v1` (H-flipped) y `crater_3m_v1` (H-flipped).
    - Reutilización de los muros de sacos de arena (`sandbag_wall_2m_v1`) y madejas de alambre.
  - Reducción drástica del número de baldosas únicas en el pool global.
- **Métricas de tiles**:
  - 1 banda: 221 tiles
  - 3 bandas: 652 tiles
  - 7 bandas pool: **1220 tiles** (reducción de 261 tiles frente a los 1481 de n04)
  - Peor ventana 33x25: **416-428 tiles** (**PASS** del límite duro VRAM < 440)

---

## Iteración n06 - Cierre, Hoja de Biblioteca 4x y Escena de Referencia 3D
- **Cambios realizados**:
  - Generación de la hoja de contacto completa de la biblioteca de piezas: `nomans_library_sheet.png` y ampliación 4x `nomans_library_sheet_4x.png` con escala rotulada en metros (0m, 2m, 5m a 17,9 px/m) y 4 orientaciones por pieza.
  - Modelado y render de la **escena de referencia en 3D** completa (`nomans_reference_band.png` y `nomans_reference_band_3x.png`): una banda de 26,8 x 14,3 m montada íntegramente en 3D en Blender con oclusión y sombras proyectadas entre objetos.
  - Medición de la escena 3D continua de referencia: arroja **313 tiles únicos** en una sola banda (demostrando experimentalmente por qué una escena continua no se puede usar directamente en VRAM sin la técnica de estampas sobre baldosas).
  - Ensamblado final del carril de 6 pantallas (1152 px) `nomans_lane.png` con paredes laterales de 16 px, sprites de Marine (31 px = 2,0 m), Skeleton y Charger, y recuadro de pantalla DS 256x192.
  - Verificación de costuras: diferencia media entre filas limítrofes = 9,6 px (totalmente imperceptible).
- **Métricas de tiles finales (n06)**:
  - 1 banda: 221 tiles
  - 3 bandas: 652 tiles
  - 7 bandas pool: 1220 tiles
  - Total 9 bandas carril: 1220 tiles
  - Peor ventana visible (33x25): **428 tiles** (**PASS** < 440 VRAM)

---

## Tabla Resumen de Iteraciones

| Iteración | Piezas / Cambios | 1 Banda | 3 Bandas | 7 Bandas Pool | Peor Ventana (33x25) | Límite VRAM (<440) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **n01** | Calibración 17,9 px/m + baldosas + crater 5m + wire 4m + coil 1.5m | 242 | 567 | 1582 | 475 | FAIL |
| **n02** | Cráteres 3m, 8m + Sacos de arena + Huellas JSON | 224 | 523 | 2080 | 561 | FAIL |
| **n03** | 24 piezas completas (tanque 7m, cañón 4m, cuerpos, huesos, casquillos) | 286 | 664 | 2480 | 590 | FAIL |
| **n04** | Zonas de respiración + Trinchera transversal + Rotaciones ortogonales | 221 | 652 | 1481 | 423 | **PASS** |
| **n05** | Reutilización con volteo hardware (H-flip) para sellos clave | 221 | 652 | 1220 | 416-428 | **PASS** |
| **n06** | Hoja 4x con escala + Escena 3D de referencia + Carril 6 pantallas final | 221 | 652 | 1220 | 428 | **PASS** |

