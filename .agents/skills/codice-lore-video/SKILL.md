---
name: codice-lore-video
description: >-
  Genera vídeos verticales (9:16, 1080×1920) locutados con ElevenLabs CLI para TikTok,
  Reels y YouTube Shorts sobre el lore de personajes y enemigos del Códice de Nintendo DS,
  usando únicamente las animaciones y fichas del Códice sin revelar gameplay.
---

# Códice Lore Video (`codice-lore-video`)

Flujo estandarizado para crear vídeos verticales de lore estilo *Blasphemous* para redes sociales, usando **ElevenLabs CLI** (`elevenlabs`) + **FFmpeg** + **Pillow**. Generar un vídeo debe costar escribir el guion y ejecutar un comando.

---

## Reglas de Oro (aprendidas e innegociables)

1. **Guion contra `LORE.md`**, iterado con el usuario salvo que ya traiga el texto cerrado.
   - **Escritura aspiracional y mitológica (no literal):** nunca describir lo que el espectador ya ve (colores, «su haz»); contar la culpa, el dogma y la condena que el píxel no puede decir.
   - **Nombres cruzados:** cada historia nombra a personajes de otras (Martín, Bartolomé, Elías, Gaspar…), para que los vídeos se refuercen entre sí.
   - **Frase final del personaje:** un aforismo corto y emotivo, dicho con la voz del personaje (no la del narrador).
   - **Identidad sin etiquetas, pero sin ambigüedad (feedback 2026-11-17, Remedios):** el eje LGBT de `LORE.md` se cuenta sin decir «trans», «lesbiana»… pero tiene que entenderse a la primera en el móvil. «Eligió su nombre» se quedó corto (parecía un simple cambio de nombre); funcionó un hecho concreto y el cargo del Tribunal: «En la pila la bautizaron con nombre de varón» + «vestir de mujer y renegar del nombre que Dios le dio». Propón al usuario dos versiones (una clara y otra más velada) y recomienda la clara.
2. **Retención (medido en TikTok e Instagram, 2026-11):** casi todo el público se decide en los 2–3 primeros segundos.
   - **Nunca un primer fotograma en negro:** el personaje y el título se ven desde el instante 0 (sin fundido de entrada) y la voz arranca casi enseguida.
   - **Empezar por la frase más fuerte de la historia**, no por el contexto («Dios le abrió el pecho…», no «Elías era capellán…»). El contexto viene después.
   - **Duración:** 50–60 s funcionó algo mejor que un recorte a 38 s con el mismo arranque (una sola prueba; señal débil).
   - **La imagen cambia con la narración:** un plano por frase (`cortes`), con la puesta en escena pensada para cada vídeo (quién mira dónde, quién se mueve, quién sale de cuadro), no reglas genéricas ni un giro en bucle.
3. **Nomenclatura estricta:**
   - Usar siempre **`CÓDICE · <ROMANO>`** (ej. `CÓDICE · II`), **nunca** `BESTIARIO`.
   - **Prohibido mencionar un nombre del juego** (ni `DungeonDS` ni ningún título provisional como `Penitencia`).
   - **Cierre estándar:** `PRÓXIMAMENTE` / `en tu Nintendo DS` (en voz, pantalla y subtítulo). La DS solo aparece al final.
   - **Sin etiquetas de rol** como `(Masa)` en la ficha de doble pantalla de la DS (si la captura la tiene, enmascarar con `#000000`).
4. **Capas en 1080×1920 (fondo `#000000`):**
   - **Capa visual:** cabecera `CÓDICE · <N>` + `<NOMBRE>` arriba; el personaje debajo (caja de 840 px de alto desde `y = 340`), escalado con vecino más próximo.
   - **Subtítulos justo debajo del personaje** (`MarginV = 600`): `Palatino Linotype` 54, negrita, marfil, contorno negro, máximo 2 líneas, siguiendo literalmente el audio.
   - **El 30 % inferior de la pantalla queda vacío:** ahí TikTok e Instagram ponen el nombre de la cuenta y la descripción, que taparían los subtítulos.
5. **Cierre sin gameplay (por defecto):** mosaico animado 2×2 de los personajes del Códice sobre negro durante *"Próximamente en tu Nintendo DS"*, salvo que el usuario pida enseñar gameplay.
6. **Pregunta moral para pedir comentarios (desde 2026-11-17):** los vídeos tenían buenas vistas y casi ningún comentario porque cada historia queda cerrada. Tras la cita, `> Pregunta: «¿…?»`: el narrador hace una pregunta moral sobre la historia y dice «Deja tu veredicto en los comentarios»; la pregunta queda escrita arriba hasta el final, también sobre el mosaico.
   - **De respuesta corta:** sí/no o elegir entre dos («¿Cobarde… o el único valiente?»). Nada de «¿tenéis dudas de lore?», que obliga a pensar una pregunta.
   - **Dentro del mundo:** «veredicto», no «comenta»; el espectador hace de Tribunal.
   - **Arriba y como subtítulo:** mientras el narrador la dice, la pregunta sale también como subtítulo además de escrita arriba; el usuario prefirió dejar las dos (2026-11-17).
   - **Se paga con tiempo de historia:** se recortan unos 10 s de frases de contexto del medio; nunca el arranque ni la cita.
   - **Fuera del vídeo:** la misma pregunta abre el texto del post y va fijada como primer comentario.
   - **Medir:** comentarios por cada 1.000 vistas, en la tabla de `## Publicado` del lote, y comprobar que la retención final no cae.

---

## Estilo visual de los planos (decidido 2026-11-16)

- **Composición metafórica, no escena de juego:** fondo negro, sin suelo ni baldosas. Encima solo personajes y props sueltos que cuentan algo (una vela, una lápida, bancos volcados, columnas, el relicario). Que no parezca una captura del juego.
- **A escala:** los props guardan la proporción del juego respecto al personaje (la columna mide casi 4 veces a Elías; el banco le llega a la rodilla) y la misma densidad de píxel que el sprite del Códice. Si el render de la DS se queda pequeño o en otro ángulo, se re-renderiza el prop desde su modelo 3D: es barato y preferible a ampliar de más. **Nunca encoger un prop al dibujarlo** (feedback 2026-11-17): la vela se renderizaba grande y se reducía al 45 %, y sus píxeles salían más finos que los de la monja; se nota. Un prop se renderiza ya al tamaño final (`w` en `render_video_props.py`) y se dibuja al mismo factor entero y NEAREST que el sprite; para comprobarlo, ampliar 3-4× NEAREST el prop junto al personaje y comparar el tamaño de los bloques.
- **Props en `assets/videos/props/<prop>/`** (`color.png`, `shadow.png`, `meta.json` con la altura en metros): re-renderizados con `tools/props/render_video_props.py` a la densidad del Códice (Elías mide 143 px = 2 m; columna 7,5 m, banco 1,75 m). Estilos `A|B|C` (negro y escala real / con suelo y sombras / escala metafórica): leyenda de `assets/videos/guiones/lote-01.md`.
- **El guion lo contiene todo:** cada plano dice qué se ve (personaje, animación, dirección y props); los ajustes de producción se apuntan en el guion para poder rehacer el vídeo ejecutando el generador.

---

## Voz y audio (ElevenLabs CLI)

- **Narrador:** `Carmelo - Mature, Mysterious and Clear` (`voice_id`: `5egO01tkUjEzu7xSSE8M`), modelo `eleven_multilingual_v2`, generado **frase por frase** con pausas reales entre bloques (sin acelerones; subtítulos sincronizados).
- **Voces de personaje:** diseñadas a medida (`elevenlabs text-to-voice design`, 3 muestras; el usuario elige). Siempre pedir **castellano peninsular** explícitamente («from Madrid, Spain… NOT Latin American»).
  - **Ajustes estables** (`stability 0.65`, `style 0.15`): con más emoción la voz pierde el acento y alarga palabras (pasó con Jimena y con el «nos» de Aldonza).
  - **Mejor aún: recortar la frase de la muestra elegida** y usarla tal cual con `archivo:<ruta>` en la tabla de voces. Suena exactamente como lo que el usuario aprobó. Para eso, el texto de la muestra empieza por la frase final del personaje.
  - La cuenta tiene un tope de 10 voces creadas; `archivo:` no gasta hueco.
  - **Dos voces a la vez** (`A + B`): el generador las iguala de volumen antes de mezclarlas. Si los ritmos no casan, mejor repartir la frase entre ellas.
- **Música de fondo:** `assets/music/cathedral_battle_loop.wav` en bucle al 9 % con fade-in de 1,5 s y fade-out de 2,5 s.

---

## Flujo recomendado: lotes desde un archivo de guiones

Un lote es un único markdown: `assets/videos/guiones/lote-01.md` es el ejemplo y su **leyenda es la referencia completa de la sintaxis**. Resumen:

- `## NN · CÓDICE · <N> — <TÍTULO>`; partes `### Parte N · <animación>[ + <animación B>] · <modo> [· modificadores]`; una frase por línea `- `; la frase final `> Nombre: «…»`.
- **Modo `cortes`:** un plano por frase con su etiqueta `[…]` al inicio: `cerca`, dirección (`S` de frente … `N` de espaldas), y trayectos `DIR origen>destino` o por personaje `A DIR …` / `B DIR …` con posiciones `centro izq der fuera-izq fuera-der arriba abajo fuera-arriba fuera-abajo`.
- **Trayectos solo con el exvoto** (`exvoto_walk`, `exvoto_walk_b`): es el único con la zancada medida (`STRIDE_PX_FRAME` en el script); con otro personaje, medirla antes o los pies resbalan.
- **Ritmo:** `--paso natural` por defecto (anda a su ritmo y llega antes); `--paso lento` estira el paso a todo el plano.
- **Animaciones para vídeo:** cualquier carpeta de `assets/sprites/bestiary/<anim>/dirs/`. Para variar sin clones, generar variantes (p. ej. `exvoto_walk_b` con `EXVOTO_VARIANT=b` en `tools/characters/build_exvoto.py`).

```bash
# Prueba gratis (sin voz): comprueba encuadre, planos y subtítulos
python .agents/skills/codice-lore-video/scripts/render_guiones.py --guiones <lote.md> --solo 01 --sin-voz
# Real (gasta créditos solo en frases nuevas; la caché de voz es compartida)
python .agents/skills/codice-lore-video/scripts/render_guiones.py --guiones <lote.md> [--solo 01,03] [--prefijo prueba]
```

Salida: `assets/videos/loreXX_NN_<titulo>.mp4` y una tira de 6 fotogramas en `walkthroughs/lore-lote-XX/assets/` (`--tiras` lo cambia). Antes de entregar, mirar fotogramas de cada plano (arranque, cortes, trayectos), no solo la tira.

---

## Formato largo de un solo vídeo (JSON, heredado)

`scripts/render_codice_video.py --config <ruta_config.json>`: un único GIF, tarjeta de doble pantalla opcional y segmentos `char_1` → `card` → `char_2` → `outro`. Se mantiene por los cuatro primeros vídeos (`codice_0N_*.mp4`); lo nuevo se hace con lotes.

```json
{
  "codice_header": "CÓDICE · II",
  "character_name": "EL EXVOTO",
  "voice_id": "5egO01tkUjEzu7xSSE8M",
  "character_gif": "assets/sprites/bestiary/exvoto_walk/dirs/0_S.gif",
  "card_png": "walkthroughs/bestiario/assets/02_exvoto.png",
  "card_mask_rect": [64, 202, 105, 215],
  "mosaic_gifs": ["assets/sprites/bestiary/corazon_disparo/dirs/0_S.gif", "..."],
  "bgm_wav": "assets/music/cathedral_battle_loop.wav",
  "work_dir": "<scratch_dir>",
  "output_mp4": "<scratch_dir>/codice_02_exvoto.mp4",
  "phrases": [
    {"id": "p01", "text": "En la Catedral, ninguna plegaria queda sin respuesta...", "pause": 0.40,
     "segment": "char_1", "subtitles": ["En la Catedral, ninguna plegaria\\Nqueda sin respuesta..."]}
  ]
}
```
