# Walkthrough: Vídeo de Lore de El Ojo del Tribunal (`feat/video-lore-ojo`)

## Resumen

Generado el vídeo vertical de lore (9:16, 1080×1920) para redes sociales (TikTok, Reels, YouTube Shorts) correspondiente al cuarto penitente del Códice, **El Ojo del Tribunal** (`CÓDICE · IV`), utilizando la skill estandarizada `codice-lore-video`.

### Claves de Dirección Artística y Montaje

1. **Sprite animado frontal (`0_S.gif`, 160×160 px nativos):**
   - Ilustración frontal centrada que luce el barrido completo de la linterna del juicio (rotación al 50 % de velocidad respecto al paso), revelando la cuenca ciega sustituida por el farol y la túnica monástica.
   - Escalado píxel-perfecto con `flags=neighbor` sobre fondo negro puro (`#000000`), centrado con aire superior e inferior.
2. **Tarjeta de doble pantalla de Nintendo DS (`walkthroughs/bestiario/assets/04_ojo.png`):**
   - Transición central a la ficha auténtica capturada de la ROM, limpia y sin etiquetas de rol provisionales.
3. **Locución y música:**
   - Voz de Carmelo (`eleven_multilingual_v2`, `stability=0.28`, `similarity_boost=0.80`, `style=0.60`, `speed=1.0`) sintetizada frase a frase con pausas dramáticas de silencio (`0.50 s – 0.85 s`).
   - Guion con enfoque aspiracional y mitológico (evitando descripciones literales de color o elementos evidentes en pantalla).
   - Música de fondo `cathedral_battle_loop.wav` atenuada al 9 % (`volume=0.09`) con fundidos suaves al inicio y al final.
4. **Subtitulado Palatino Linotype:**
   - Subtítulos `.ass` en color marfil (`#F2ECE0`) con fileteado negro, tipografía serif solemne (`Palatino Linotype`), `MarginV = 240` (respetando la zona inferior reservada para la interfaz de las plataformas) y sincronización milimétrica con cada frase.
5. **Cierre estándar del Códice:**
   - Pantalla final con mosaico 2×2 animado de los 4 penitentes sobre fondo negro puro y texto `PRÓXIMAMENTE / en tu Nintendo DS`.

---

## Evidencia Visual

### Tira de Control de Fotogramas (Secuencia completa)
![Tira de control del vídeo](assets/ojo_video_preview_strip.png)

### Fotogramas Individuales por Etapa

| 1. Apertura (`CÓDICE · IV · EL OJO DEL TRIBUNAL`) | 2. Ficha Nintendo DS | 3. Sentencia y Comportamiento | 4. Cierre Mosaico (`PRÓXIMAMENTE`) |
| :---: | :---: | :---: | :---: |
| ![Apertura](assets/frame_01_char1.png) | ![Ficha DS](assets/frame_02_card.png) | ![Retorno Ilustración](assets/frame_03_char2.png) | ![Cierre Mosaico](assets/frame_04_outro.png) |

---

## Ficha Técnica del Vídeo Generado

- **Archivo:** `walkthroughs/codice-ojo/assets/codice_04_ojo.mp4` (centralizado en `assets/videos/codice_04_ojo.mp4`)
- **Resolución:** 1080×1920 px (relación de aspecto vertical 9:16)
- **Duración:** 01:10.73 (~70,7 s)
- **Tasa de refresco:** 30 fps progresivo (H.264 / AAC)
- **Peso:** 8,3 MB (8.735.218 bytes)
- **Palabras de locución:** 114 palabras (10 frases, ritmo pausado con pausas dramáticas)
