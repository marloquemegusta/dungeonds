# Sesión 18: Perfil de rendimiento de Mario frente al héroe

## Método

- Blender 5.2.1 LTS; Windows.
- FBX medidos: `assets/characters/custom/mario_camisa_blanca.fbx` (el mismo contenido SHA-256 que el archivo de Descargas) y `Walking.fbx`.
- Dos renders directos por asset, con valores UI: 48×48 px, 16 muestras, outline y 8 direcciones × 8 frames (64 imágenes); métricas de etapa como medianas.
- Después medí una llamada real a cada endpoint del servidor recién reiniciado: `/api/fbx-actions` y `/api/render`. Esas cifras son una ejecución por asset.

## Resultados

| Métrica | Héroe Nigromante | Mario | Diferencia |
|---|---:|---:|---:|
| FBX | 19,86 MB | 14,08 MB | Mario −29 % |
| Vértices | 5.851 | 9.701 | Mario +66 % |
| Polígonos | 6.994 | 19.390 | Mario 2,77× |
| Huesos | 37 | 65 | Mario +76 % |
| Imágenes/materiales | 2/1 | 6/1 | Mario +4 imágenes |
| Importación FBX | 0,310 s | 0,443 s | +0,133 s |
| Setup de escena y bounds animados | 0,084 s | 0,124 s | +0,040 s |
| Render de 64 frames | 1,894 s | 2,018 s | +0,124 s |
| Job directo completo, postproceso/GIF incluido | 4,975 s | 5,214 s | +0,239 s (+4,8 %) |
| Consulta inicial de animaciones por HTTP | 2,54 s | 2,51 s | −0,03 s |
| Render por endpoint HTTP | 4,54 s | 4,95 s | +0,41 s (+9 %) |
| Selección + render, suma de endpoints | 7,08 s | 7,46 s | +0,38 s (+5,4 %) |

El servidor que atendía `localhost:8088` seguía vivo desde las **10:17**, antes de que el archivo de código cambiara a las **11:45**. Su proceso Blender importaba Mario con `bpy.ops.import_scene.fbx(filepath=fbx)`, sin `use_image_search=False`; esa versión seguía haciendo la búsqueda recursiva que ya se había quitado del código. Reinicié el servidor y medí los endpoints reales.

## Conclusión

La diferencia actual no es grande: en HTTP, Mario renderizó en **4,95 s** y el héroe en **4,54 s**; listar acciones añade ~**2,5 s** para ambos cuando no está en caché. Mario tiene 2,77× los polígonos y 76 % más huesos, pero no explica la demora extrema que veías: provenía del servidor antiguo, que continuaba usando la búsqueda recursiva.

El servidor está reiniciado con la corrección. Si la pestaña conserva un spinner o una petición antigua, recárgala y vuelve a renderizar Mario.
