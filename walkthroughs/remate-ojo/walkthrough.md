# Walkthrough — Ejecución del Ojo del Tribunal: arrancarle el farol y patearlo (`feat/remate-ojo`)

**Fecha:** 2026-11-21
**Rama:** `feat/remate-ojo` (worktree `.worktrees/remate-ojo`)
**Diseño:** `DESIGN.md` §6.13.8 (ejecuciones / glory kills)

## Qué se ha hecho

Una animación de ejecución del **Ojo del Tribunal** con el **estilo visual de las ejecuciones del Exvoto**: misma
cámara diagonal (45° de acimut, 30° de elevación), mismos pases de render y misma post (borde duro al alfa 110,
sombra al 45 %, GIF 4x NEAREST a 60 ms por fotograma). El héroe le **agarra el farol que lleva sobre los hombros**
(es su cabeza), se lo **arranca de un tirón**, lo **tira al suelo** y le **da una patada** con la animación de patada
que el usuario dejó en el inbox.

**La animación del inbox no se ha movido ni borrado:** `assets/inbox/Zombie Kicking.fbx` se lee desde el repo
principal y solo se usa como dato de pose (no se copia al worktree ni se toca).

### Secuencia (24 fotogramas a 60 ms ≈ 1,44 s, 4x NEAREST)

| Fotogramas | Qué pasa |
| :--- | :--- |
| 0–1 | El héroe entra y el Ojo, arrodillado y tambaleándose, se inclina hacia él. |
| 2 | **Agarre:** las dos manos del héroe cierran sobre la jaula del farol. |
| 3–4 | **Tirón y arranque:** el héroe se echa atrás y el farol se desprende del cuello. **El cuerpo se queda de pie, sin cabeza**, y empieza a tambalearse. Chispas y vidrio del farol. |
| 5–6 | El héroe lo voltea y lo lanza al suelo. |
| 7–8 | El farol cae a los pies del héroe y se queda a ras de suelo. |
| 9–17 | El Ojo se tambalea, ciego, mientras el héroe se coloca y sube la pierna (arranque de la patada). |
| **18** | **Contacto:** el pie le entra al cuerpo y **el Ojo se desploma**; el farol sale despedido a ras de suelo, hacia el espectador. |
| 19–23 | El Ojo cae de espaldas y queda hecho un montón; el farol se queda al pie. |

## Cómo se ha hecho

- **Escena y escala reales:** héroe a escala 1,0 (0,93 m de modelo) y Ojo a 1,32 (lectura de +40 % sobre el héroe,
  como en su sprite de 56 px). Cámara ortográfica a 46 px/m y ancla de los pies del héroe en el píxel (48, 60).
- **El farol es geometría del propio Ojo:** al importarlo se le cambia el reparto de pesos del cuello a `Head` (ya lo
  hacía `build_ojo.py`) y aquí, en el fotograma del agarre, se **hornea la malla ya deformada y se corta** por el
  cuello con `cut_object` (corte dentado y sección rellena en rojo oscuro). Quedan tres piezas: tronco + cabeza de la
  mano, y el farol suelto.
- **El cuerpo caído es rígido y aguanta hasta el golpe:** del 4 al 17 se tambalea sin farol sobre sus pies (vaivén
  lateral de ±4° con periodo de 5,6 fotogramas, más un cabeceo lento), y solo en el 18, al entrarle el pie, se vuelca
  hacia atrás sobre su cadera y se apoya en el suelo. Así el remate no se «gasta» antes de la patada.
- **El farol no vuela:** se apoya en el suelo en el 8 y, cuando la patada lo roza, sale a ras (velocidad (1,4, −1,6,
  0,7) m/s) hacia el espectador, sin arco alto.
- **La patada es el clip del inbox, retargetizado:** se copia la **rotación en espacio de mundo** de la cadena
  cadera–columna–piernas (método de delta de `build_ojo.py`) girada +90° porque el FBX mira a −Y y el héroe a +X;
  las longitudes de hueso distintas escalan el alcance solas. Se juega a velocidad casi natural (≈2 fotogramas del
  clip de 30 fps por fotograma de celda) usando el tramo del **hachazo descendente** (clip 13→53), que es el que
  encaja con un objeto en el suelo.
- **Punto de contacto:** se calcula con un pre-pase (se posa al héroe con el fotograma de contacto y se lee el
  tobillo), y el farol se coloca exactamente ahí en el suelo. La patada no se inventa a ojo.
- **Manos sujetas por IK:** los objetivos de las manos se calculan sobre la jaula y **siguen al farol** mientras se
  lo lleva al pecho.

## Evidencia

- GIF de control 4x: [`assets/ojo_remate_4x.gif`](assets/ojo_remate_4x.gif)
- Hoja de contacto 3x de los 24 fotogramas: [`assets/ojo_remate_sheet.png`](assets/ojo_remate_sheet.png)
- Fotogramas 1x en [`assets/frames/`](assets/frames/)

## Verificación

- Comprobado a ojo, fotograma a fotograma, sobre la hoja de contacto: el agarre toca (hueco de las manos 0,000 m en el
  fotograma 2), el farol sale del cuello, el cuerpo **sigue de pie** del 4 al 17 tambaleándose, cae solo en el 18 con el
  golpe y el farol queda a ras junto a él. El héroe no se sale del encuadre en ningún fotograma.
- **No se ha integrado en la ROM** (`remate_sprites.c` solo conoce Exvoto y Cireneo) ni se ha medido en la DS.
  Es una ronda de diseño para aprobar el gesto.

## Pendiente

- Aprobación del gesto por el usuario y, si se aprueba, decisión de celda (12 fotogramas no dan para arranque +
  lanzamiento + patada: cabría una versión de 20–24 fotogramas o partir la acción en dos remates).
- Enlace con la mecánica: el Ojo hoy no se remata (es el ancla que obliga a subir, §6.13.9), así que integrarlo
  cambia la sala; decidir antes de programar.
- Copiar el visor de la patada si se quiere jugar el clip entero (aquí solo el hachazo).

## Notas

- Scripts nuevos: `tools/characters/ds_remate_ojo.py` (render por pases) y
  `tools/characters/ds_remate_ojo_post.py` (composición 1x + GIF 4x).
- Se regeneran los clips derivados del Ojo en el worktree con `build_ojo.py` (no se versionan).
- Ninguno de los MDs de arquitectura cambia de cifras con esta entrega; sí se apunta el gesto en `DESIGN.md` §6.13.8
  como prototipo pendiente de aprobación.
