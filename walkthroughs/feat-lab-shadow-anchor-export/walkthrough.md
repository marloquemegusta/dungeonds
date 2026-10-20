# Walkthrough: Exportación Completa de Sombras, Anchor y Datos de Mapa (Colisión/Oclusión)

**Sesión / Rama:** `feat/lab-shadow-anchor-export` en `.worktrees/feat-lab-shadow-anchor-export`  
**Fecha:** 2026-10-20  
**Herramientas:** FBX-Web-Renderer Lab (`tools/lab/FBX-Web-Renderer-parity.js`, `FBX-Web-Renderer-offline.html`), Playwright Headless Chromium.

---

## 1. Resumen Ejecutivo

En esta sesión se ha completado la exportación técnica integral de datos de simulación y renderizado para Nintendo DS desde el laboratorio web autónomo:
1. **Cálculo y Exportación Automática de Anchor y Bounds:**
   - Proyección 3D $\rightarrow$ 2D del punto de contacto con el suelo `(0, 0, 0)` bajo cámara ortográfica dimétrica.
   - Escaneo dirección por dirección (0..7) de los frames del sprite para obtener el píxel opaco más bajo (`dirGroundAnchors`), el bounding box exacto (`dirBounds`) y el anclaje global compatible con `PLAYER_ANCHOR_X`/`PLAYER_ANCHOR_Y`.
   - Sustitución del offset hardcodeado en `drawDsSimulator`: ahora el personaje se dibuja exactamente en `screenX - anchorX`, `screenY - dirGroundAnchorY`, logrando alineación milimétrica entre los pies y el suelo.
2. **Generador y Exportador de Sombras del Personaje (`generateCharacterShadows`):**
   - Proyección planar de los triángulos 3D del personaje sobre el plano $Y=0$ siguiendo el vector de luz principal (Key light de Blender).
   - Generación del atlas de sombras NDS de `768x96` px (8 direcciones de `96x96` px con anclaje en `(48, 48)`).
   - Generación de máscaras NDS de 4 bits empacadas (`(hi << 4) | lo` con niveles 0..15, $96 \times 96 / 2 = 4608$ bytes por dirección) y bounding boxes de sombra (`shadowBounds`).
   - Exportación de `${name}_shadow.png`, carpeta `shadows/` con las 8 sombras individuales y archivo de cabecera C auto-generado `${name}_nds_shadow_anchor.h` listo para compilar en el motor NDS.
   - Dibujo en tiempo real de la sombra proyectada real en el canvas del simulador DS.
3. **Exportación Completa del Mapa 3D (`exportMapPackage`):**
   - `${name}_world.png` y `${name}_map_settings.json`.
   - `${name}_collision.json` con matriz de transitabilidad/walkability celda a celda ($4 \times 4$ px).
   - `${name}_collision.png`: mapa visual en blanco y negro (blanco = transitable, negro = muros y obstáculos).
   - `${name}_occlusion.png`: máscara de píxeles cuya altura 3D en el mundo supera el umbral de oclusión ($> 0.65$ m) para permitir la oclusión del personaje detrás de columnas y pilares en el motor DS.

---

## 2. Evidencia Visual en el Simulador NDS

![Simulador NDS con Anchor Real y Sombra Proyectada](C:/Users/malfonso/.gemini/antigravity/brain/6e2bd23d-eb11-49d4-920f-5c9402c66d29/lab_shadow_anchor_simulator.png)

![Detalle del Simulador DS (Recorte)](C:/Users/malfonso/.gemini/antigravity/brain/6e2bd23d-eb11-49d4-920f-5c9402c66d29/ds_simulator_crop.png)

---

## 3. Verificación Automatizada

Ejecución del test Playwright headless (`tools/lab/test_shadow_anchor_export_headless.cjs`):
- **Cero errores fatales de consola:** `errors.length === 0`.
- **Anchor Data:**
  - Anchor global calculado: `(24, 41)`.
  - 8 direcciones de apoyo calculadas en `dirGroundAnchors`.
  - 8 cajas envolventes de sprite calculadas en `dirBounds`.
- **Sombras del Personaje:**
  - `state.shadowCanvas`: atlas de `768x96` px (8 celdas de `96x96` px).
  - `state.shadowBounds`: 8 cajas con ancho y alto $>0$ (`[25, 35, 40, 32]`).
  - `state.shadowMasks4Bit`: 8 arrays de 4608 bytes empacados en 4 bits.
- **Exportación de Paquetes:**
  - ZIP de personaje con `${name}_shadow.png`, carpeta `shadows/`, `${name}_nds_shadow_anchor.h` y `settings.json`.
  - ZIP de mapa con `${name}_world.png`, `${name}_map_settings.json`, `${name}_collision.json`, `${name}_collision.png` y `${name}_occlusion.png`.
