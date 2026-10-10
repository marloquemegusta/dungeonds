# Sesión 17: Búsqueda acotada de texturas FBX

## Resumen

Se eliminó la búsqueda recursiva de texturas desde rutas de FBX obsoletas, que en el modelo de Mario podía recorrer todo C:\. Blender importa ahora sin búsqueda global y el Shader Lab busca mapas externos únicamente en carpetas .fbm hermanas del FBX.

## Hallazgo

- mario_camisa_blanca.fbx guardaba rutas de mapas con siete niveles ..; el importador default (use_image_search=True) acababa buscando desde la raíz del disco.
- Importación con opciones actuales: **229,97 s**. Sin búsqueda recursiva y conservando animación: **0,85 s**.
- La carpeta .fbm tiene cinco PNG de mapas PBR. El FBX contiene versiones empacadas de los cinco; sus tamaños coinciden con los PNG, así que esta carpeta es redundante para ese archivo.
- Los FBX sin .fbm siguen funcionando; solo se consulta la carpeta cuando una imagen no está empacada y la ruta del FBX no existe.

## Implementación

- La consulta de acciones importa con use_image_search=False.
- El worker de render importa igual y relocaliza imágenes externas faltantes buscando sus nombres únicamente bajo carpetas .fbm junto al FBX.
- Se conservan mapas embebidos y rutas externas que ya existan.

## Verificación

- Render completo de Shader Lab para Mario a **48×48 px, 16 muestras**: **6,44 s**; generó el collage de ocho direcciones.
- Evidencia: [collage del render](assets/mario-48px-after.gif).
