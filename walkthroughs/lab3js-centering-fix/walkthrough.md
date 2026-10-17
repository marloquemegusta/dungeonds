# Walkthrough: Corrección del Centrado Multimodelo (Mario, Henar, Wizard, Necron) en Three.js

## Contexto y Causa Raíz

Al probar modelos como Mario, Henar, Wizard o Necron en `FBX-Web-Renderer-offline.html`, los sprites aparecían descentrados orbitando en círculos amplios (desviación de hasta 15 píxeles) a lo largo de las 8 direcciones, mientras que el Charger parecía mantenerse relativamente centrado.

### Hallazgos de la Inspección
1. **Unskinned Box3 Corrupto:** En la función de carga `Lf`, Three.js utilizaba `Box3.setFromObject(e)` para auto-centrar el modelo restando `a.x` y `a.z`. En Three.js, `Box3` evalúa los vértices crudos en bind-pose sin aplicar las matrices de huesos ni deformaciones del skinning. En modelos de Tripo/Mixamo, la geometría cruda está desplazada por convención de coordenadas (`Z ≈ -50` cm), lo que provocaba que `Lf` sumara `+49.97` cm a `e.position.z` (casi 1 metro de desviación del origen del rig).
2. **Órbita Circular en Rotación Multidireccional:** El rig rota en `modelRoot` alrededor de `(0, 0)`. Con el personaje posicionado a $Z \approx 0.9$ m del pivote, rotar a lo largo de las 8 direcciones hacía que el personaje describiera una órbita circular de 15 píxeles de radio (`cx` oscilaba de 8.6 a 38.4 px en celda de 48 px). El encuadre de la cámara se expandía para abarcar la órbita completa (2.76 m), reduciendo el tamaño del personaje a la mitad.
3. **Pivote Canónico de Rig en Blender:** En Blender (`shader_lab_server.py`), la armadura y mallas se emparentan al `CameraRig` manteniendo su posición de origen (`root_anchor` en `(0, 0, 0)`). El modelo rota sobre su eje vertical de rig/pies y nunca sobre el centro geométrico no deformado.

---

## Cambios Implementados

1. **Guarda de Robustez en `setFromObject` (`FBX-Web-Renderer-parity.js`):**
   - Agregada verificación `if (!object) return this;` en el interceptor de `hr.prototype.setFromObject` para evitar excepciones `TypeError: Cannot read properties of null` durante cargas asíncronas de archivos.

2. **Reemplazo del Loader `Lf`:**
   - Para modelos humanoides/rigged (con huesos), se mantiene la posición horizontal en `(0, 0)` fija, alineada con el pivote de la armadura.
   - Apoyo en el suelo (`minY` de vértices posados vía `posedPoints`) en $Y = 0$.
   - Para modelos estáticos sin huesos, se centra horizontalmente usando el centroide real de los vértices.
   - Cálculo de escala visual del viewport basado en la altura posada real (`maxY - minY`) en vez de la caja estática cruda.

3. **Corrección de Encuadre en `Qf` (Renderizado de Sprites):**
   - El Paso 1 asegura `app.model.position.x = 0; app.model.position.z = 0;` para modelos rigged.
   - Eliminado el offset empírico hardcodeado `- 1.48 * pixelWorld` en `center.upAxis`, alineándolo con la fórmula exacta de Blender `((_min_y + _max_y) * 0.5)`.

4. **Suite de Verificación Automatizada Multimodelo:**
   - `tools/lab/test_models_centering.py` creado y validado para inspeccionar centroides y cajas delimitadoras en modo Chromium headless.

---

## Resultados y Métricas de Validación

### Coincidencia con Blender (IoU) y Centrado

| Modelo | IoU Silueta Previo | IoU Silueta Nuevo | Centrado `cx` (8 dirs) | Coincidencia de Dirección |
| :--- | :---: | :---: | :---: | :---: |
| **Mario** (`mario_camisa_blanca.fbx`) | 12.5% | **94.21%** | 23.5 ± 0.3 px | **100% (8/8)** |
| **Henar** (`henar_top_kaki.fbx`) | ~14% | **95.58%** | 23.5 ± 0.7 px | **100% (8/8)** |
| **Wizard** (`wizard.fbx`) | ~13% | **94.91%** | 23.5 ± 0.5 px | **100% (8/8)** |
| **Necron** (`tripo_convert...necron.fbx`) | ~10% | **95.1%** | 23.5 ± 0.4 px | **100% (8/8)** |
| **Charger** (`Run.fbx`) | 80.87% | **84.68%** | 23.6 ± 0.5 px | **100% (8/8)** |

---

## Evidencia Visual

### Mario: Antes vs Después de la Corrección
![Mario Paridad Final](C:/Users/malfonso/.gemini/antigravity/brain/87191940-e539-4d39-ba94-21e77626671b/mario_compare_after.png)

### Henar: Paridad con Blender (95.6% IoU)
![Henar Paridad Final](C:/Users/malfonso/.gemini/antigravity/brain/87191940-e539-4d39-ba94-21e77626671b/henar_compare_after.png)

### Wizard: Paridad con Blender (94.9% IoU)
![Wizard Paridad Final](C:/Users/malfonso/.gemini/antigravity/brain/87191940-e539-4d39-ba94-21e77626671b/wizard_compare_after.png)

### Charger: Paridad con Blender (84.7% IoU)
![Charger Paridad Final](C:/Users/malfonso/.gemini/antigravity/brain/87191940-e539-4d39-ba94-21e77626671b/charger_compare_after.png)
