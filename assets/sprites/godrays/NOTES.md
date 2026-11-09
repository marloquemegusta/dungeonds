# Prerendered Godrays (Haces de Vidriera) - Brief v2 Log

Fecha: 2026-11-08  
Motor: Blender 5.2.1 LTS (Cycles, GPU OptiX, RTX 3000 Ada)  
Toolchain: scripts reproducibles en `tools/godrays_art/`  

## 1. Verificación Física Obligatoria
- **Rayos estrictamente paralelos:** Sol con `angle = 0.0`. En la imagen final (comprobado columna a columna), el haz mantiene una sección transversal constante (41-42 px de grosor vertical) desde la ventana hasta el suelo sin ensancharse jamás.
- **Proyección de la vidriera en el suelo:** La mancha del suelo reproduce la geometría, bandas de color y tracería de plomo oscuro opaco de la vidriera (lancetas gemelas con parteluz de piedra en lancet; rosetón de 12 sectores radiales en rose).
- **Color en el volumen:** El haz volumétrico mantiene los haces de color correspondientes a las secciones de la vidriera a lo largo de su trayectoria.
- **Aislamiento de luz pura:** Luz = Render A (Sol ON) − Render B (Sol OFF), recortando a ≥ 0 sobre negro puro `(0, 0, 0)`.
- **Geometría de cámara de juego:** Ortográfica, elevación 30°, orientada a lo largo de la nave (+Y). Escala exacta de 17,9 px/m horizontal (suelo achatado 2:1 en vertical; marine de 2 m mide 31 px).

## 2. Mediciones Reales de los PNGs Finales (256×128 px)

| Archivo | Dimensiones | Max RGB | Intensidad Pico | Media R, G, B | Cobertura Activa |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ray_lancet_vitral.png` | 256×128 px | [160, 107, 175] | 175/255 (68.6%) | [8.36, 3.99, 7.05] | 21.8% |
| `ray_lancet_amber.png` | 256×128 px | [175, 114, 48] | 175/255 (68.6%) | [11.97, 7.26, 1.33] | 27.5% |
| `ray_rose_vitral.png` | 256×128 px | [175, 118, 167] | 175/255 (68.6%) | [10.27, 4.97, 7.87] | 25.4% |

> [!NOTE]
> Todas las variantes cumplen estrictamente el contrato: intensidad máxima ≤ 70% (~175/255), esquinas vacías al 100% en negro puro (0, 0, 0) para ahorrar tiles VRAM en la Nintendo DS.

## 3. Diario de Iteraciones y Correcciones
1. **Iteración 1 (Diagnóstico inicial):**
   - Se analizó el intento anterior en `tools/godrays_art/test_*.py`.
   - Fallo detectado: la cubierta (Roof) exterior del modelo cubría X de -15 a +35 a 12 m de altura, bloqueando los rayos del sol antes de alcanzar la ventana exterior. Además, la cámara (Z=17.8) quedaba por encima del techo opaco.
   - Solución: Techo restringido al interior de la nave y marcado con `visible_camera = False` para bloquear luz cenital parásita sin ocluir la visión ortográfica del juego.

2. **Iteración 2 (Color y Gestión de Color AgX vs Standard):**
   - Blender 5.2 activa AgX por defecto, lo que alteraba los valores de color y aplastaba la saturación.
   - Solución: Configuración explícita de `view_transform = 'Standard'` en Cycles. Transmisión a través del Transparent BSDF verificada físicamente con sombras coloreadas.

3. **Iteración 3 (Paralelismo y Esparcimiento Volumétrico):**
   - Con anisotropía alta (0.70 forward), la luz que llegaba a la cámara (a 90° del haz) era muy tenue en comparación con el suelo.
   - Solución: Anisotropía ajustada a 0.15 y densidad volumétrica a 0.18-0.20, delimitando el volumen al corredor del haz. Resultado: haz visible (60-95 RGB) y mancha del suelo brillante (160-175 RGB), con bordes perfectamente paralelos (41-42 px de altura constante).

4. **Iteración 4 (Downsampling y Contrato de Esquinas Negras):**
   - Render a 4x (1024×512) y reducción con filtro Lanczos a 256×128.
   - Aplicación de curva suave para asegurar que las esquinas vacías sean 100% `(0, 0, 0)`, evitando niebla tenue que gastaría memoria en los sprites de 4 bpp de la DS.

## 4. Contact Sheet de Revisión
El archivo `preview_sheet.png` (1360×1770 px) contiene la comparación a 1x y a 4x NEAREST sobre el suelo de piedra de la catedral con el sprite del marine para validación de escala.
