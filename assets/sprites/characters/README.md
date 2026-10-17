# assets/sprites/characters/

Esta carpeta es el directorio de destino canónico para los spritesheets 2D de personajes.

## Cómo añadir nuevos personajes desde el Shader Lab Web:
1. Abre `tools/lab/FBX-Web-Renderer-offline.html` en el navegador.
2. Carga el modelo `.fbx` (disponibles en `assets/models/characters/`).
3. Ajusta iluminación, contraste (1.50) y parámetros de renderizado.
4. Pulsa en **Renderizar 8 direcciones** y luego **Exportar paquete completo** (descargará `<nombre>_sprite_lab.zip`).
5. Descomprime o arrastra la carpeta del paquete aquí:
   ```
   assets/sprites/characters/<nombre>/
     ├── <nombre>_sheet.png          (hoja de sprites 8 direcciones x 8 frames)
     ├── <nombre>_shadow.png         (máscara de sombra)
     ├── <nombre>_anchor.json        (ancla y metadatos)
     └── ... (GIFs y frames individuales)
   ```
