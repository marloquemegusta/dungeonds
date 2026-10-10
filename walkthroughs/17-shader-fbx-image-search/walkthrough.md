# Sesión 17: FBX sin búsqueda de sidecar .fbm

## Resumen

Se eliminó la búsqueda recursiva de texturas desde rutas de FBX obsoletas, que en el modelo de Mario podía recorrer todo C:\. Blender importa ahora sin búsqueda global y el Shader Lab ignora las carpetas .fbm.

## Hallazgo

- mario_camisa_blanca.fbx guardaba rutas de mapas con siete niveles ..; el importador default (use_image_search=True) acababa buscando desde la raíz del disco.
- Importación sin búsqueda recursiva y conservando animación: **0,85 s**.
- El FBX de Mario contiene mapas PBR empacados, así que el sidecar .fbm no es necesario para este asset.

## Implementación

- La consulta de acciones y el worker importan con use_image_search=False.
- El Shader Lab no inspecciona ni busca carpetas .fbm; usa los mapas empacados dentro del FBX.

## Verificación

- Copié el FBX a una carpeta temporal sin sidecar .fbm; el render completo a **48×48 px, 16 muestras** terminó correctamente en **7,7 s**.
- Evidencia: [collage del render](assets/mario-48px-after.gif).
