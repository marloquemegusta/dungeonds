# Visor FBX web offline con look DungeonDS

## Entrega

- Visor autónomo: tools/lab/FBX-Web-Renderer-offline.html.
- Copia lista para abrir: C:\Users\malfonso\Downloads\FBX-Web-Renderer-offline.html.
- Conserva Three.js y las dependencias de render/exportación embebidas; no requiere servidor ni recursos CSS/JS externos.

## Cambios

- Presets DungeonDS, neutro y antorcha; el preset DungeonDS reproduce los colores, intensidades y direcciones de las luces compartidas del laboratorio. Los controles permiten ajustar intensidades y colores de key, fill, rim y ambiente.
- Sombras de la luz principal activables. Three.js y Blender no comparten el mismo renderizador ni gestión de color, así que el preset aproxima el look; no promete igualdad píxel a píxel.
- El tamaño visible se expresa como porcentaje del cuadro y muestra una estimación en píxeles según la resolución elegida. La cámara calcula el encuadre con las poses que se van a exportar en las ocho direcciones.
- Animación in-place activada por defecto: fija X/Z de los canales de posición Root/Hips, conserva Y y permite desactivar el bloqueo para restaurar el clip original.

## Verificación

- Node parseó los dos scripts embebidos; los IDs son únicos, los controles están presentes y no hay referencias a scripts u hojas de estilo externos.
- Prueba sintética: reconoce Armature.bones[mixamorig:Hips].position, fija X/Z, conserva Y y restaura los valores al desactivar in-place.
- La prueba visual/headless no se pudo ejecutar: el navegador del entorno bloquea automatización de la página file://. No se generó captura; conviene abrir el archivo en el navegador y probar un FBX con ciclo de caminar.
- El detector Impeccable solo conserva como aviso la transición de anchura del indicador de progreso, que comunica el avance del render.
