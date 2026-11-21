# Walkthrough — Ejecución del Ojo del Tribunal: arrancarle el farol y patearlo (`feat/remate-ojo`)

**Fecha:** 2026-11-21
**Rama:** `feat/remate-ojo` (worktree `.worktrees/remate-ojo`)
**Diseño:** `DESIGN.md` §6.13.8 (ejecuciones / glory kills)

## Qué se ha hecho

Una animación de ejecución del **Ojo del Tribunal** con el **estilo visual de las ejecuciones del Exvoto**: misma
cámara diagonal (45° de acimut, 30° de elevación), mismos pases de render y misma post (borde duro al alfa 110,
sombra al 45 %, GIF 4x NEAREST a 60 ms por fotograma). El héroe le **agarra el farol que lleva sobre los hombros**
(es su cabeza), se lo **arranca de un tirón**, lo **tira al suelo**, el cuerpo descabezado **se levanta tambaleándose**
y, cuando le llega la **patada**, cae **hacia atrás** con la animación de muerte del inbox y se queda muerto.

Los clips del inbox **no se han movido, copiado ni borrado**: `assets/inbox/Zombie Kicking.fbx` y
`assets/inbox/Falling Back Death.fbx` se leen desde el repo principal y solo se usan como dato de pose.

### Secuencia (38 fotogramas a 60 ms ≈ 2,28 s, 4x NEAREST)

| Fotogramas | Qué pasa |
| :--- | :--- |
| 0–1 | El héroe entra; el Ojo está arrodillado para que le llegue el farol del hombro. |
| 2 | **Agarre:** las dos manos del héroe cierran sobre la jaula del farol (hueco de las manos 0,000 m). |
| 3–4 | **Tirón y arranque:** el farol se desprende del cuello (borde dentado y sección en rojo oscuro). Chispas y vidrio. |
| 4–11 | El cuerpo **se levanta** del suelo, tambaleándose (`k` de arrodillado a de pie con un pequeño rebote). |
| 5–8 | El héroe voltea el farol y lo tira: vuela, cae a sus pies en el 8 y se queda a ras. |
| 11–17 | El Ojo, ya **de pie y descabezado**, se tambalea (vaivén de ±4,4° con periodo de 5,2 fotogramas). El héroe sube la pierna. |
| **17** | **Contacto:** el pie del héroe toca el cuerpo del Ojo (clip 23 de la patada) **y ese mismo fotograma arranca el desplome**: el cuerpo empieza a irse hacia atrás en el 18 y acelera. |
| 17–29 | **Desplome:** clip `Falling Back Death` desde su fotograma 7 (el de la reacción), a 2 fotogramas de clip por celda. Se vuelca, los brazos se abren y cae de espaldas. |
| 30–37 | El cuerpo queda muerto en el suelo. El héroe **recupera la pose**: del 30 al 37 la patada se mezcla de vuelta a su reposo (el clip de patada acaba en un idle de zombi; no se deja así). |

### Ocho direcciones

Las 8 variantes de dirección del remate (dir 0 = S … dir 7 = SE, las mismas que `remate_sprites.c`) se generan
girando **la cámara y el sol** alrededor de la pareja, que se queda en el sitio: equivale a girar el remate bajo una
luz fija, como haría el juego. Cada dirección tiene su GIF y su carpeta de fotogramas.

## Cómo se ha hecho (y qué se arregló de la ronda anterior)

- **El farol es la cabeza y se corta por PESO, no por un plano.** La ronda anterior partía la malla con un plano que
  pasaba por el cuello; como el Ojo va inclinado, el plano se llevaba **226 vértices del antebrazo derecho y 52 de la
  mano**: el héroe arrancaba farol + trozo de brazo y el brazo salía volando. Ahora la malla se parte por el **peso del
  hueso `Head`** (`split_by_head`): la mitad de cabeza recibe un borde dentado común y una tapa de cera, la del cuerpo
  la tapa opuesta. **El brazo y la mano de piedra se quedan en el cuerpo.** El cuerpo ya no se hornea: se queda
  *skinned*, así que se deforma con la animación (antes era un bloque rígido que se volcaba).
- **El desplome es la animación del inbox, no una rotación procedural.** `Falling Back Death.fbx` (79 fotogramas,
  Mixamo) se retargetiza al esqueleto del Ojo: por hueso se copia el **delta de rotación de mundo respecto al
  fotograma 7** (el de la reacción) **relativo a su padre**, y se compone sobre la pose de pie del Ojo; la traslación
  de cadera se escala por 0,52 y se gira −100° para que el cuerpo caiga hacia +X (alejándose del héroe) y no se salga
  de la celda. Cae de espaldas, con los brazos abiertos y una pierna arriba, como el clip.
- **La sincronía patada–caída es un solo fotograma.** Antes el pie «entraba» donde el clip baja la pierna al suelo
  (a los pies del propio héroe) y el cuerpo se caía por su cuenta. Ahora el fotograma de contacto es el clip 23
  (el pie ya está dentro del cuerpo, a 0,55 m de alto) y el desplome arranca **en ese mismo fotograma**; el 18 es el
  seguimiento (clip 25) y a partir de ahí el cuerpo acelera. No hay ni un fotograma en el que el cuerpo se mueva sin
  que el pie lo esté tocando.
- **La patada no se corta a medias.** Se retargetiza también la **cadena de brazos, hombros, cuello y cabeza** (antes
  los brazos se quedaban en la pose de andar y el héroe acababa encorvado con los brazos de zombi). Del 30 al 37 la
  pose del último fotograma del clip (49) se **mezcla por slerp** con la pose de reposo del héroe, así que la
  animación termina con el héroe de pie, normal.
- **El farol no vuela:** al rozarlo el pie en el 19 sale un palmo, rueda y se para (desplazamiento amortiguado de
  ~0,3 m; antes salía con parábola a 1,4 m/s y se iba de la celda).
- **Escala y encuadre:** 38 px/m (exactamente la del remate del Exvoto en `generate_remate_sprites.py`) y celda de
  96×96. La celda queda justa: el cuerpo caído llega al borde derecho en cuatro direcciones (tabla abajo).
- **Punto de contacto:** se calcula con un pre-pase (se posa al héroe con el fotograma de contacto y se lee el pie).
- **Manos sujetas por IK:** los objetivos se calculan sobre la jaula y siguen al farol mientras se lo lleva al pecho.

## Evidencia

- Las 8 direcciones para revisar: [`assets/ojo_remate_8dirs.html`](assets/ojo_remate_8dirs.html) (GIF 4x de cada una).
- GIF por dirección: `assets/ojo_remate_d0_4x.gif` … `assets/ojo_remate_d7_4x.gif`.
- Hoja comparativa del fotograma de contacto en las 8: [`assets/ojo_remate_contacto_8dirs.png`](assets/ojo_remate_contacto_8dirs.png)
- Fotogramas 1x de cada dirección en `assets/dir_<d>/fNN.png`.

## Verificación

- Agarrador: hueco de las manos 0,000 m en el fotograma 2.
- Farol limpio: la pieza arrancada son 1.158 caras de la cabeza (sin un solo vértice de brazo, hombro ni mano).
- Contacto: pie del héroe en (0,68, 0,17, 0,71) — dentro del cuerpo, a la altura de la cadera, en el fotograma 17.
- Desplome: en el 17 la cadera del Ojo está a 0,61 m (de pie) y en el 29 a 0,30 m, con el cuerpo tumbado y la
  manta (malla) apoyada en el suelo (se corrige la penetración fotograma a fotograma).
- Recuperación: en el 37 el héroe vuelve a la pose de reposo exacta (cadera 0,47 m, cabeza 0,82 m, pie 0,09 m).
- Encuadre en las 8 direcciones (caja de los personajes en píxeles de celda, 96×96, medido sobre los pases `lit`):

| dir | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| x | 9–96 | 0–96 | 15–84 | 13–75 | 0–87 | 0–96 | 12–81 | 21–83 |
| y | 11–77 | 10–72 | 8–78 | 6–80 | 5–77 | 7–78 | 9–84 | 11–80 |

  En 0, 1, 4 y 5 el gesto **toca el borde** (no se recorta nada, pero no sobra sitio): es lo que ocupa la caída
  completa en una celda de 96 px a 38 px/m. La celda del Exvoto se queda justa para una ejecución de 38 fotogramas con
  caída larga; si se aprueba el gesto, hay que decidir celda (el Cireneo ya usa 116×116).
- **No se ha integrado en la ROM** (`remate_sprites.c` solo conoce Exvoto y Cireneo) ni se ha medido en la DS.
  Es una ronda de diseño para aprobar el gesto.

## Pendiente

- Aprobación del gesto por el usuario y, si se aprueba, decisión de celda: 38 fotogramas no caben en la celda de 12
  del Exvoto; habría que decidir tamaño de celda y si se parte la acción en dos remates.
- Enlace con la mecánica: el Ojo hoy no se remata (es el ancla que obliga a subir, §6.13.9), así que integrarlo
  cambia la sala; decidir antes de programar.

## Notas

- Scripts: `tools/characters/ds_remate_ojo.py` (render por pases, los dos clips del inbox) y
  `tools/characters/ds_remate_ojo_post.py` (composición 1x + GIF 4x + hoja + HTML).
- Se regeneran los clips derivados del Ojo en el worktree con `build_ojo.py` (no se versionan).
- Ninguno de los MDs de arquitectura cambia de cifras con esta entrega; sí se apunta el gesto en `DESIGN.md` §6.13.8
  como prototipo pendiente de aprobación.
