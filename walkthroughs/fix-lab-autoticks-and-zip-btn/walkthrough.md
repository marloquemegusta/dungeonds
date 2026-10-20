# Walkthrough - Sesión 64: Cálculo Automático de Ticks/Frame (AnimTicks) y Persistencia del Botón de Descarga ZIP

## Resumen Ejecutivo

En esta sesión se resuelven dos problemas críticos de usabilidad, paridad cinemática y exportación en el entorno de pre-renderizado `tools/lab/FBX-Web-Renderer-parity.js` y su homólogo autónomo `tools/lab/FBX-Web-Renderer-offline.html`:

1. **Persistencia Permanente del Botón de Exportación ZIP de Personaje (`#downloadPackageBtn`):**
   - **Causa raíz diagnosticada:** Al completar el renderizado completo de las 8 direcciones (`Qf`), la rutina base de actualización de GIFs `Np(e)` ejecutaba `op.style.display = 'none'` (donde `op` apuntaba a `#btnExportZip` / `#downloadPackageBtn`) e intentaba mostrar `ap` (`#btnDownloadAll`), el cual había sido purgado del DOM por `restructureLayout()`. Como consecuencia, el botón de exportación de personaje desaparecía por completo del panel de controles `#row-char-exports`.
   - **Solución implementada:** Se neutralizó la manipulación que ocultaba `op` en `Np`, se estandarizaron los identificadores canónicos `#downloadPackageBtn` y `#renderBtn` manteniendo compatibilidad bidireccional mediante alias con `#btnExportZip` y `#btnRender`, se forzó `display: inline-flex !important;` en la hoja de estilos inyectada y se añadió un `MutationObserver` centinela que previene cualquier ocultación inadvertida antes, durante o después de renderizar.

2. **Cálculo Automático de Ticks por Frame (`state.autoAnimTicks` / `#animTicks`) a 60 Hz:**
   - **Cálculo cinemático:** A partir de la duración del clip activo (`clip.duration` en segundos) y del recuento de frames de exportación (`frameCount = getExportFrameCount()`), se calcula automáticamente:
     $$\text{autoTicks} = \max\left(1, \min\left(30, \operatorname{round}\left(\frac{\text{clip.duration} \times 60}{\text{frameCount}}\right)\right)\right)$$
     (con fallback a 3 ticks si la duración del clip es nula o no hay animación).
   - **Reactividad y overrides (`dataset.userEdited`):** El valor se asigna a `state.autoAnimTicks` y actualiza automáticamente el input `#animTicks` salvo que el usuario lo haya modificado manualmente (`dataset.userEdited = "true"`). Este flag se resetea al cargar un nuevo modelo, cambiar de animación o vaciar el input, idéntico al comportamiento de `#stride3d`.
   - **Telemetría y Badge UI (`#strideMetricsHint`):** Se integró un elemento `#strideMetricsHint` y se enriqueció `updateDsMetricsBadge()` y el HUD interactivo de `drawDsSimulator()` para exhibir la velocidad resultante en formato punto fijo 8.8 (`speed8.8 = round((effPx * 256) / (frameCount * ticks))`), p.ej. `3t/f @60Hz -> speed8.8=181`.

---

## Cambios Técnicos Detallados

### 1. `tools/lab/FBX-Web-Renderer-parity.js`

- **Shims de Resolución de IDs Duales:**
  Implementados interceptores ligeros para `document.getElementById` y `document.querySelector` que resuelven indistintamente `#downloadPackageBtn` $\leftrightarrow$ `#btnExportZip` y `#renderBtn` $\leftrightarrow$ `#btnRender`.
- **Hoja de Estilos Inyectada (`injectStyles`):**
  Añadida la regla `#downloadPackageBtn, #btnExportZip { display: inline-flex !important; align-items: center !important; justify-content: center !important; visibility: visible !important; }`.
- **Estructuración del DOM (`restructureLayout`):**
  - Adición de `#animTicksVal` y telemetría `#strideMetricsHint` bajo el grupo de zancada.
  - Asegurada la inserción del botón de descarga en `#row-char-exports` con `id="downloadPackageBtn"` y su centinela `MutationObserver`.
- **Cálculo de Ticks y Zancada (`updateCharacterStrideMetrics` & `updateStrideUI`):**
  - Extracción de `clip.duration` del clip activo y evaluación de `autoTicks = Math.max(1, Math.min(30, Math.round((clipDuration * 60) / frameCount)))`.
  - Actualización de `animTicksVal`, `#strideMetricsHint` y `updateDsMetricsBadge()`.
- **Ciclo de Renderizado (`Qf`):**
  - Asegurado que al concluir el renderizado (tanto al retornar como en el bloque `finally`), el botón `#downloadPackageBtn` queda activo (`disabled = false`, `hidden = false`, `display = 'inline-flex'`).
- **Interactividad del Simulador DS:**
  - Actualización reactiva de métricas (`updateStrideUI()`) en movimientos con ratón o teclado (`WASD`/flechas).
  - Reseteo automático de `dataset.userEdited` al cargar nuevos modelos FBX (`Ap`) o demos procedimentales (`sp.onclick`).

### 2. `tools/lab/FBX-Web-Renderer-offline.html`

- Actualizados los botones base del markup HTML a `id="downloadPackageBtn" data-legacy-id="btnExportZip"` y `id="renderBtn" data-legacy-id="btnRender"`.
- Modificada la rutina `Np` para que establezca `op.style.display = 'inline-flex', op.hidden = false, op.disabled = false` en lugar de ocultarlo.
- Sincronizada la paridad completa mediante `tools/lab/build_offline_renderer.py`.

---

## Verificación Automatizada

Se implementó el test headless de Playwright `tools/lab/test_autoticks_and_zip_btn_headless.cjs` con las siguientes aserciones superadas al 100%:

| Test Case | Condición Probada | Resultado |
| :--- | :--- | :--- |
| **TC1: Presencia DOM** | Existencia y visibilidad inicial de `#renderBtn`, `#downloadPackageBtn`, `#animTicks` y `#strideMetricsHint`. | **PASS** |
| **TC2: Auto AnimTicks** | Modelo demo (duración 1.0s, 8 frames): cálculo exacto $\operatorname{round}(1.0 \times 60 / 8) = 8$ ticks. | **PASS** |
| **TC3: Reactividad Slider** | Cambio de slider `#frameCount` a 16: $\operatorname{round}(1.0 \times 60 / 16) = 4$ ticks. | **PASS** |
| **TC4: Duraciones Custom** | Simulación de clips de 0.40s (3 ticks) y 0.80s (6 ticks) a 8 frames. | **PASS** |
| **TC5: Override Manual** | Modificación manual de `#animTicks` a 12: flag `dataset.userEdited = "true"`, protección contra sobreescritura y reseteo al vaciar. | **PASS** |
| **TC6: Visibilidad Render** | `#downloadPackageBtn` permanece visible (`offsetParent !== null`, `hidden === false`) antes, durante y después del renderizado completo. | **PASS** |
| **TC7: Exportación ZIP** | Ejecución de `exportPackage()`: generación válida de ZIP con spritesheet, atlas de sombra, header C NDS y `settings.json` con `ticksPerFrame = 3` y `speedFixed8_8 > 0`. | **PASS** |
| **TC8: Consola Limpia** | 0 errores de consola (`errors.length === 0`). | **PASS** |

---

## Evidencia Visual

### Antes de Renderizar
El botón de descargar ZIP `#downloadPackageBtn` está disponible e integrado en la barra de exportaciones del personaje, y `#animTicks` refleja el cálculo automático (`8t (auto)` para el clip de 1.0s):

![Laboratorio Antes de Renderizar](C:/Users/malfonso/.gemini/antigravity/brain/7288fbac-294b-48c0-b805-e2790ea21fee/lab_before_render.png)

### Tras Renderizar Animación Completa (#renderBtn)
Al pulsar el botón rojo de renderizar y completarse las 8 direcciones, el botón `#downloadPackageBtn` permanece perfectamente visible, habilitado y listo para empaquetar el paquete ZIP:

![Laboratorio Tras Renderizar](C:/Users/malfonso/.gemini/antigravity/brain/7288fbac-294b-48c0-b805-e2790ea21fee/lab_after_render.png)
