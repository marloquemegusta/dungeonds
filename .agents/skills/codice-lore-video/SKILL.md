---
name: codice-lore-video
description: >-
  Genera vídeos verticales (9:16, 1080×1920) locutados con ElevenLabs CLI para TikTok,
  Reels y YouTube Shorts sobre el lore de personajes y enemigos del Códice de Nintendo DS,
  usando únicamente las animaciones y fichas del Códice sin revelar gameplay.
---

# Códice Lore Video (`codice-lore-video`)

Flujo estandarizado para crear vídeos verticales (~1 minuto) de lore estilo *Blasphemous* para redes sociales, usando **ElevenLabs CLI** (`elevenlabs`) + **FFmpeg** + **Pillow**.

---

## Reglas de Oro (aprendidas e innegociables)

1. **Iterar primero el guion con el usuario** (a menos que ya traiga el texto cerrado). Objetivo: ~115–130 palabras (~55–68 s con pausas dramáticas).
   - **Escritura aspiracional y mitológica (no literal):**
     - **Prohibidas las descripciones visuales obvias o «baratas»:** nunca describir lo que los ojos del espectador ya ven en pantalla (p. ej. colores evidentes como «verde», «verduzca» o términos genéricos como «su haz»).
     - **Foco narrativo:** elevar el lore evocando la culpa, el dogma, el castigo, la penitencia y la psicología de la condena. El guion debe contar lo que el píxel por sí solo no puede decir.
2. **Nomenclatura estricta:**
   - Usar siempre **`CÓDICE · <ROMANO>`** (ej. `CÓDICE · II`), **nunca** `BESTIARIO`.
   - **Prohibido mencionar un nombre del juego** (ni `DungeonDS` ni ningún título provisional como `Penitencia`).
   - **Cierre estándar:** `PRÓXIMAMENTE` / `en tu Nintendo DS` (en voz, pantalla y subtítulo).
   - **Sin etiquetas de rol** como `(Masa)` en la ficha de doble pantalla de la DS (si la captura la tiene, enmascarar con `#000000`).
3. **Separación estricta de capas en 1080×1920 (fondo `#000000`):**
   - **Capa visual (arriba/centro, `y = 150..1430`):** cabecera `CÓDICE · <N>` + `<NOMBRE>`, sprite animado escalado con `flags=neighbor` (píxel perfecto) o ficha de doble pantalla de la DS.
   - **Capa de subtítulos (siempre debajo, `MarginV = 240`):** tipografía constante de principio a fin (`Palatino Linotype`, `Fontsize = 54`, negrita, marfil `#F2ECE0`, contorno negro), máximo 2 líneas por bloque, siguiendo **literalmente** cada frase del audio. Nunca pisa la capa visual ni entra en la zona inferior de botones de TikTok/Reels.
4. **Cierre sin gameplay (por defecto):** mostrar el mosaico animado 2×2 de los 4 personajes del Códice sobre negro puro (`#000000`) durante *"Próximamente en tu Nintendo DS"*, salvo que el usuario pida explícitamente enseñar gameplay.

---

## Configuración de Voz y Audio (ElevenLabs CLI)

- **Voz por defecto:** `Carmelo - Mature, Mysterious and Clear` (`voice_id`: `5egO01tkUjEzu7xSSE8M`).
- **Modelo:** `eleven_multilingual_v2`.
- **Sliders de emoción:** `stability = 0.28`, `similarity_boost = 0.80`, `style = 0.60`, `speed = 1.0`.
- **Anti-acelerones:** generar la locución **frase por frase** en bloques cortos a `speed = 1.0` (nunca un texto de 60 s en una sola llamada) y añadir pausas reales de silencio (`0.35 s – 0.85 s`) entre bloques. Así se evitan acelerones de ritmo y los subtítulos quedan sincronizados al milisegundo.
- **Música de fondo:** `assets/music/cathedral_battle_loop.wav` en bucle al `9 %` de volumen (`volume=0.09`) con fade-in de `1.5 s` y fade-out de `2.5 s`.

---

## Cómo ejecutarlo

1. Consultar el lore base del personaje en `source/bestiary.c` (o en la rama correspondiente si aún no se ha mergeado).
2. Acordar el guion dividido en bloques cortos con el usuario.
3. Crear un archivo JSON de configuración para el episodio (p. ej. en el directorio `scratch/` de la sesión) siguiendo el esquema de `scripts/render_codice_video.py`.
4. Ejecutar:
   ```bash
   python .agents/skills/codice-lore-video/scripts/render_codice_video.py --config <ruta_config.json>
   ```
5. Extraer al menos 2–3 fotogramas del MP4 generado con `ffmpeg` y revisarlos visualmente antes de entregar el vídeo al usuario.
6. **Almacenamiento centralizado:** todos los vídeos finales se conservan en `assets/videos/<nombre>.mp4`. El script `render_codice_video.py` copia automáticamente el MP4 resultante a `assets/videos/`.

---

## Esquema del JSON de entrada

```json
{
  "codice_header": "CÓDICE · II",
  "character_name": "EL EXVOTO",
  "voice_id": "5egO01tkUjEzu7xSSE8M",
  "character_gif": "assets/sprites/bestiary/exvoto_walk/dirs/0_S.gif",
  "card_png": "walkthroughs/bestiario/assets/02_exvoto.png",
  "card_mask_rect": [64, 202, 105, 215],
  "mosaic_gifs": [
    "assets/sprites/bestiary/corazon_disparo/dirs/0_S.gif",
    "assets/sprites/bestiary/exvoto_walk/dirs/0_S.gif",
    "assets/sprites/bestiary/cireneo_walk/dirs/0_S.gif",
    "assets/sprites/bestiary/ojo_walk/dirs/0_S.gif"
  ],
  "bgm_wav": "assets/music/cathedral_battle_loop.wav",
  "work_dir": "<scratch_dir>",
  "output_mp4": "<scratch_dir>/codice_02_exvoto.mp4",
  "phrases": [
    {
      "id": "p01",
      "text": "En la Catedral, ninguna plegaria queda sin respuesta...",
      "pause": 0.40,
      "segment": "char_1",
      "subtitles": ["En la Catedral, ninguna plegaria\\Nqueda sin respuesta..."]
    }
  ]
}
```

Los valores válidos de `segment` en orden son: `"char_1"`, `"card"`, `"char_2"`, `"outro"`. (Si un episodio no usa tarjeta de doble pantalla, se puede omitir `"card"` y usar `"char_1"` → `"outro"`).
