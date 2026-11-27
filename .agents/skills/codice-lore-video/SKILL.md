---
name: codice-lore-video
description: >-
  Genera vídeos verticales (9:16, 1080×1920) locutados con ElevenLabs CLI para TikTok,
  Reels y YouTube Shorts sobre el lore de personajes y enemigos del Códice de Nintendo DS,
  usando únicamente las animaciones y fichas del Códice sin revelar gameplay.
---

# Códice Lore Video (`codice-lore-video`)

Flujo estandarizado para crear vídeos verticales de lore estilo *Blasphemous* para redes sociales, usando **ElevenLabs CLI** (`elevenlabs`) + **FFmpeg** + **Pillow** para voz y planos, y **Remotion** con la plantilla del tema para el montaje final (regla 11). Generar un vídeo debe costar escribir el guion y ejecutar tres comandos.

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
   - **Subtítulos justo debajo del personaje:** caja del tema visual (abajo) en `y = 1145`, máximo 2 líneas, siguiendo literalmente el audio; las citas en cursiva.
   - **El 30 % inferior de la pantalla queda vacío:** ahí TikTok e Instagram ponen el nombre de la cuenta y la descripción, que taparían los subtítulos.
5. **Cierre sin gameplay (por defecto):** mosaico animado 2×2 de los personajes del Códice sobre negro durante *"Próximamente en tu Nintendo DS"*, salvo que el usuario pida enseñar gameplay.
6. **Pregunta moral para pedir comentarios (desde 2026-11-17):** los vídeos tenían buenas vistas y casi ningún comentario porque cada historia queda cerrada. Tras la cita, `> Pregunta: «¿…?»`: el narrador hace una pregunta moral sobre la historia y dice «Deja tu veredicto en los comentarios»; la pregunta queda escrita arriba hasta el final, también sobre el mosaico.
   - **De respuesta corta:** sí/no o elegir entre dos («¿Cobarde… o el único valiente?»). Nada de «¿tenéis dudas de lore?», que obliga a pensar una pregunta.
   - **Dentro del mundo:** «veredicto», no «comenta»; el espectador hace de Tribunal.
   - **Arriba y como subtítulo:** mientras el narrador la dice, la pregunta sale también como subtítulo además de escrita arriba; el usuario prefirió dejar las dos (2026-11-17).
   - **Se paga con tiempo de historia:** se recortan unos 10 s de frases de contexto del medio; nunca el arranque ni la cita.
   - **Fuera del vídeo:** la misma pregunta abre el texto del post y va fijada como primer comentario.
   - **Medir:** comentarios por cada 1.000 vistas, en la tabla de `## Publicado` del lote, y comprobar que la retención final no cae.
7. **Narrativa clara, no solo misterio (feedback 2026-11-19, Lope):** el borrador del 07 era enigmático y «no quedaba claro nada». Cada vídeo debe entenderse a la primera sin haber visto el Códice: quién es, qué hizo o le hicieron, por qué, y qué es hoy. El modelo es Remedios.
   - **La culpa o la condena, como hecho concreto:** «calló» no basta; funcionó «Íñigo tenía rango para plantar cara al Tribunal (decir "yo también le amo") y no se atrevió, por conservar el mando». Si el lore deja un hueco, proponer al usuario 2-3 opciones con recomendación, y lo elegido se escribe en `LORE.md` antes de renderizar.
   - **Las pistas a otras historias** (la mortaja vacía de Martín, el corazón de Elías) van al final y son un extra, no la historia.
   - **Una idea que cierra el círculo:** el estandarte tocó el suelo cuando ardió Lope y Íñigo juró que no volvería a caer, que explica por qué cose las mortajas «para que nadie se quede atrás». Un detalle así vale más que más contexto.
   - **Parejas del mismo sexo:** hay varias en el lore y es coherente si el castigo por amar es parte de la historia de ese personaje (Íñigo y Lope). Si solo es una historia de amor y pérdida (Martín y Bartolomé) basta «se amaban», sin castigo. No repetir el mismo motivo en dos vídeos seguidos.
8. **Puesta en escena de los vídeos del Abanderado (feedback 2026-11-19):**
   - **Sin cortejo por defecto:** el sprite es `abanderado_solo`. Los monaguillos solo salen cuando la frase habla de la Columna: capitán de espaldas (`N`) en el tercio superior, a 2,3× la escala de la formación, y detrás (hacia cámara) `multitud 9` en bloque 3×3 ordenado a 0,8× (`abanderado_solo + monaguillo_walk`).
   - **`medio`:** plano de cintura para arriba, para presentar al personaje con un prop de fondo (el altar tras Íñigo); `cerca` es busto. El altar se dibuja detrás del personaje y a escala de plano general.
   - **Props con alfa:** nunca un recuadro negro opaco que corte el penacho o la melena del personaje.
   - **Ritmo lento:** andar a ritmo lento natural (`lento 1.5` en las partes de andar de Íñigo; la Columna avanza visible, no rápida). Si el usuario dice que algo anda rápido, se baja al ritmo más lento que ya aprobó.
   - **Animación a medida** cuando el Códice no tiene la que pide la escena (derrumbarse y golpear el suelo): `abanderado_derrota`, de Mixamo «Plant A Plant» espejado y retocado con `tools/characters/build_abanderado_derrota.py`. El asta cae al suelo y se recoge.
   - **Un personaje que sale como imagen del presente de otro** (el Ojo para el Tribunal): una sola aparición, sin nombre, para no confundirlo con Gaspar.
9. **Duración y primera persona (feedback 2026-11-19):** si el usuario dice que le gusta la duración, no se recorta (07: 88 s, frente a los 50-60 s de la regla 2). La cita en primera persona se dice lenta y solemne: velocidad de la voz del personaje (`CHAR_SPEED`, 0,8 para Íñigo) y una `(pausa 0.5)` en mitad de la frase.
10. **Producción simple (feedback 2026-11-20, Liebre):** el 04 llegó a 13 animaciones (9 hechas a medida) y salía peor: poses raras y una cabeza que se plegaba hacia atrás. Los vídeos con 1-3 animaciones (01, 03) no rinden peor en redes. Se rehízo con 6 animaciones ya probadas y quedó «mucho más simple y mejor».
   - **Unas 5 animaciones por vídeo como máximo** y **como mucho 1 nueva**, que sea un clip de Mixamo usado tal cual (`tools/characters/build_cireneo_clips.py` es el modelo).
   - **Nada de poses montadas a mano** (arrodillarse con un prop, tumbarse, esconderse): el exportador del lab solo aplica las rotaciones de los huesos y la traslación de la cadera, así que las poses que desplazan otros huesos se rompen.
   - **Lo difícil se cuenta sin animarlo:** con otro personaje (Inés en lugar de Bartolomé escondido), con el resultado (Bartolomé ya en la cruz) o con sonido sobre negro (`negro` + `sfx … fin`: el martillo de Tadeo).
   - **Personaje a cuerpo entero** (`cerca · entero`) en vez de busto ampliado: la silueta completa impacta más y el píxel no engorda.
   - **Si la voz de un personaje sobreactúa:** generar 3 tomas planas (estabilidad 0,95, estilo 0, velocidad 0,85, con variantes del texto), que el usuario elija y usar la elegida con `archivo:`. Las `(pausa N)` dentro de una frase corta pueden romper la entonación.
   - **Exportador del lab:** `--dirs S,SE` renderiza solo las direcciones que usa el guion (resultado idéntico al render completo); `LAB_GL=gpu` gana poco (~30 %) y da píxeles distintos de la CPU, así que no se mezcla dentro de un clip.

11. **Estilo definitivo: Remotion + la plantilla del tema (decisión del usuario, 2026-11-27).** Lo que se publica es el montaje de Remotion: misma voz y planos que el render clásico, más subtítulo palabra a palabra (palabra activa en dorado apagado), zoom por plano, golpe y destello en la cita, todo con `GameBox` (`devlog/src/theme/`). El render clásico ya no se publica: es el paso que genera voz, planos y el plan de montaje (`scratch/codice-video/<prefijo>/remotion.json`). Flujo en «Flujo recomendado», abajo. Composición genérica `LoreVideo` en `C:\codexlocal\devlog\src\lore\` (fuera del repo); las composiciones a mano anteriores (`Lore05`, `Lore11`, `Lore0201`) se borraron el 2026-11-27. `public/<id>/` pesa cientos de MB y se regenera con `prepare_lore.py`: se puede borrar tras publicar. Los devlogs finales van a `assets/videos/devlog/` (LFS).
12. **Aprendizajes del 11 (Campanero, 2026-11-24):**
    - **Props en el plano:** nada de PNG pegado; si un objeto sale, va renderizado como parte del mundo (la vela delante del Campanero se quitó por eso).
    - **Antes de modificar un modelo, mirar qué trae:** la campana ya tenía una lengua de badajo y se usó tal cual (`campana_lengua`, `tools/props/build_campana_lengua.py`). Un plano de objeto solo es una animación más en `assets/sprites/bestiary/<nombre>/` con celda 320.
    - **Animación que se ve mal en primer plano** (la cabeza de `campanero_tanido` se pliega hacia atrás): cambiarla por otra del personaje.
    - **Remotion:** en el cierre no se pone subtítulo bajo el rótulo PRÓXIMAMENTE (lo tapaba); `LoreVideo` ya lo hace así.

---

## Estilo visual de los planos (decidido 2026-11-16)

- **Composición metafórica, no escena de juego:** fondo negro, sin suelo ni baldosas. Encima solo personajes y props sueltos que cuentan algo (una vela, una lápida, bancos volcados, columnas, el relicario). Que no parezca una captura del juego.
- **A escala:** los props guardan la proporción del juego respecto al personaje (la columna mide casi 4 veces a Elías; el banco le llega a la rodilla) y la misma densidad de píxel que el sprite del Códice. Si el render de la DS se queda pequeño o en otro ángulo, se re-renderiza el prop desde su modelo 3D: es barato y preferible a ampliar de más. **Nunca encoger un prop al dibujarlo** (feedback 2026-11-17): la vela se renderizaba grande y se reducía al 45 %, y sus píxeles salían más finos que los de la monja; se nota. Un prop se renderiza ya al tamaño final (`w` en `render_video_props.py`) y se dibuja al mismo factor entero y NEAREST que el sprite; para comprobarlo, ampliar 3-4× NEAREST el prop junto al personaje y comparar el tamaño de los bloques.
- **Props en `assets/videos/props/<prop>/`** (`color.png`, `shadow.png`, `meta.json` con la altura en metros): re-renderizados con `tools/props/render_video_props.py` a la densidad del Códice (Elías mide 143 px = 2 m; columna 7,5 m, banco 1,75 m). Estilos `A|B|C` (negro y escala real / con suelo y sombras / escala metafórica): leyenda de `assets/videos/guiones/lote-01.md`.
- **El guion lo contiene todo:** cada plano dice qué se ve (personaje, animación, dirección y props); los ajustes de producción se apuntan en el guion para poder rehacer el vídeo ejecutando el generador.

---

## Tema visual

Todo texto de vídeo (cabecera, pregunta, subtítulos, cierre; también el devlog en Remotion) usa el tema común: caja de piedra roja con marco dorado del arte de inventario de la ROM y Palatino a 1 bit (13 px nativos, ampliado x5 NEAREST, sombra de 1 px). Fuente de verdad: `tools/video_theme/` (`build_kit.py` genera `kit/` y `theme.json`; `theme.py` expone `render_box(lineas, highlight=..., style="regular"|"italic")` y `wrap`). `render_guiones.py` y `render_codice_video.py` la componen como PNG con `overlay`. Remotion (`devlog/src/theme/`) lee la misma `theme.json`: tras regenerar el kit, `build_kit.py --public <devlog>/public/theme` y copiar `theme.json` a `devlog/src/theme/`.

**Regla: ningún texto de vídeo fuera del tema.** Nada de `drawtext`, ASS ni fuentes CSS propias.

## Voz y audio (ElevenLabs CLI)

- **Narrador:** `Carmelo - Mature, Mysterious and Clear` (`voice_id`: `5egO01tkUjEzu7xSSE8M`), modelo `eleven_multilingual_v2`, generado **frase por frase** con pausas reales entre bloques (sin acelerones; subtítulos sincronizados).
- **Voces de personaje:** diseñadas a medida (`elevenlabs text-to-voice design`, 3 muestras; el usuario elige). Siempre pedir **castellano peninsular** explícitamente («from Madrid, Spain… NOT Latin American»).
  - **Ajustes estables** (`stability 0.65`, `style 0.15`): con más emoción la voz pierde el acento y alarga palabras (pasó con Jimena y con el «nos» de Aldonza).
  - **Mejor aún: recortar la frase de la muestra elegida** y usarla tal cual con `archivo:<ruta>` en la tabla de voces. Suena exactamente como lo que el usuario aprobó. Para eso, el texto de la muestra empieza por la frase final del personaje.
  - La cuenta tiene un tope de 10 voces creadas; `archivo:` no gasta hueco.
  - **Dos voces a la vez** (`A + B`): el generador las iguala de volumen antes de mezclarlas. Si los ritmos no casan, mejor repartir la frase entre ellas.
  - **Velocidad por personaje:** `CHAR_SPEED` en `render_guiones.py` (0,7–1,2); para citas solemnes, 0,8.
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

Salida: `assets/videos/loreXX_NN_<titulo>.mp4` (clásico, intermedio) y una tira de 6 fotogramas en `walkthroughs/lore-lote-XX/assets/` (`--tiras` lo cambia).

**Montaje final en Remotion** (después del render real con voz):

```bash
cd C:\codexlocal\devlog
python src/lore/prepare_lore.py lote-02.md 02 lore02_02        # public/lore0202/ y src/lore/lore0202.json
# una línea en src/Root.tsx: <Composition id="Lore0202" component={LoreVideo} … defaultProps={{ info: lore0202 }} />
npx remotion render Lore0202 C:\codexlocal\dungeonds\assets\videos\lore02_02_<titulo>_remotion.mp4
```

Lo que se publica es el `_remotion.mp4`. Antes de entregar, mirar fotogramas de cada plano (arranque, cortes, cita, pregunta, cierre), no solo la tira.

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
