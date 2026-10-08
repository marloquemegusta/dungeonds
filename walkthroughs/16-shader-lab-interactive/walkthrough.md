# Sesión 16: DS Shader Lab Interactivo y Pipeline FBX Abierto

## Resumen Ejecutivo

En esta sesión se desarrolló una herramienta interactiva local para tuning de modelos 3D, iluminación Cycles y post-proceso 2D con renderizado continuo y acoplamiento cinemático para Nintendo DS, además de resolver el centrado de cámara y la selección abierta de modelos FBX.

---

## 1. Problema Diagnosticado

1. **Descentrado Vertical y Recorte Superior:**
   - La cámara isométrica enfocaba originalmente a `(0, 0, 0)` (nivel del suelo).
   - Debido al levantamiento por frame del rig para apoyar los pies en el plano de tierra, el centro de gravedad del personaje quedaba desplazado hacia arriba respecto al centro de encuadre ($Y=32$).
   - A escalas superiores a 1.40× (y especialmente a 2.00×), la cabeza superaba el margen superior ($Y < 0$) y se cortaba.
2. **Dependencia de Lista Cerrada de Modelos:**
   - Previamente, el pipeline admitía únicamente los 3 presets codificados a fuego (`hero`, `charger`, `skeleton`).

---

## 2. Solución e Implementación

### 2.1 Corrección de Centrado Vertical de Cámara
En `tools/lab/shader_lab_server.py`:
- Se evalúa dinámicamente la altura del modelo tras la deformación (`_char_height`).
- Se sitúa `CamTarget` en el punto medio vertical simétrico del personaje:
  $$\text{target\_z} = \text{char\_height} \times 0.50$$
- Se ajusta la posición de la cámara isométrica para conservar la inclinación canónica de 30° con el nuevo centro.
- **Resultado:** A escala 2.00× en el lienzo de 64×64, la cabeza se mantiene perfectamente dentro de los márgenes ($Y \in [11, 56]$ para el héroe y $[8, 56]$ para el esqueleto), sin ningún recorte.

### 2.2 Selector Dinámico y Subida de FBX
- **Descubrimiento automático:** El endpoint `/api/config` y `/api/fbx-files` escanea recursivamente `assets/` detectando todos los archivos `.fbx`.
- **Subida vía Web:** Botón nativo `📁 Subir FBX Local` en la interfaz (`tools/lab/shader_lab_ui.html`) con subida Base64 al endpoint `/api/upload-fbx` (guardado en `assets/characters/custom/`).
- **Parámetros avanzados configurables:**
  - Armature Scale (p. ej. `0.027` para rigs Maya/Mixamo de esqueletos o `1.0` para escala métrica).
  - Inclinación de cuello (`neck_pitch`).
  - Fattening/Displace óseo.
  - Selección de shader (PBR estándar vs Shader óseo limpio).
  - Zancada 3D y periodo de animación acoplados al speed fixed-point 8.8.

---

## 3. Evidencia Visual

![Héroe a Escala 2.0x Centrado](assets/hero_scale200_centered.gif)

*Collage animado en 8 direcciones generado con el nuevo centrado vertical a escala 2.00×.*

---

## 4. Archivos Clave y Estado

- `tools/lab/shader_lab_server.py`: Servidor HTTP y orquestador de bakes headless en Blender Cycles.
- `tools/lab/shader_lab_ui.html`: Interfaz web interactiva (`http://localhost:8088`).
- Trabajo integrado en `main` tras validación en worktree aislado `.worktrees/shader-lab-interactive`.
