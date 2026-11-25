# Brief común: colocar los encuentros de una sala (póster ARPG)

Worktree: `C:\codexlocal\dungeonds\.worktrees\arpg-encuentros`. Sin commit. Solo tocas las `tools/poster/salas/sala_NN.py` que te asignen (nada más: ni `poster_arpg_juego.py`, ni `source/`, ni DESIGN).

## Qué manda
- `DESIGN-ARPG.md` §12 (formaciones, reposo, emboscadas, progresión) y §10 (grupos por nave). Léelas enteras.
- Ejemplo hecho: `tools/poster/salas/sala_06.py` (`GRUPOS`, formato documentado en el docstring de `tools/poster/poster_arpg_juego.py`). x/y = pies del enemigo, locales al bloque k (k=0 = tramo de entrada, abajo; el héroe entra por abajo y sube).
- Datos de sala (bloques, nave, nivel, puertas, cofre, altar): `source/encounters_act1.c:95` `s_rooms`. Grupos de la ROM: `s_groups` (:811) y `group_of_block()` (:831): **mismo número de grupos por sala que hoy asigna la ROM** (la experiencia está equilibrada así), pero puedes elegir cuáles de la lista de su nave según la progresión de §12. Composición de cada grupo: **exacta** a §10 (p. ej. Procesión = 5 Bebés + 2 Monaguillos). Los encuentros especiales, según §7.
- Huella de props: `POSTER_DEBUG=1` imprime la huella visible de cada prop. Columnas visibles de los claustros: x=18..52 y x=138..172, base en y=127 y 287 de cada bloque.

## Reglas de oficio
1. **Nada geométrico:** ni círculos, ni cuadrados, ni filas perfectas (salvo la Muralla). Racimos irregulares, con separación variada; que parezca gente haciendo algo.
2. **Contexto de la sala:** cada grupo hace algo con lo que hay (monjas ante el altar o junto a un catre, bebés entre los bancos rotos, Ojo al fondo dominando un paso, Cireneo con línea recta libre hacia una columna).
3. **Entrada libre:** los primeros ~110 px del bloque 0 sin enemigos; ningún enemigo en huecos de puerta, encima del cofre, del altar ni de props.
4. **Radios de aviso (96 px):** que no se solapen entre grupos salvo que quieras que se despierten juntos (dilo en el nombre/comentario).
5. **Emboscadas:** solo detrás (al norte) de una pieza alta que lo tape entero en la imagen (bebé o monaguillo); en un comentario, la pista que lo delata (ruido de cera, sombra, vela). No más de una emboscada por sala salvo Osario y Monjaraña.
6. **Monjas detrás** del grupo (más al norte que la carne de cañón), los Ojos al fondo o a un lado, la Muralla entre héroe y monjas.
7. **Variedad:** en una sala, formaciones distintas entre grupos.
8. Comentario de una línea por grupo: qué enseña o qué pide al jugador.

## Comandos
`python tools/poster/poster_arpg.py --sala N --revision` (desde la raíz del worktree; ~1,5 s). Salida en `walkthroughs/arpg-encuentros/assets/{limpia,revision}/NN_*.png`. Si falla por caché concurrente (otros agentes renderizan a la vez), reintenta. Python de Windows: escribe con `newline=""`.

## Bucle
Coloca → renderiza → **mira tu imagen de revisión** (Read) → corrige lo que no cumpla las reglas → una segunda pasada como mínimo. Mira que los escondidos no asomen.

## Entrega (informe corto)
Por sala: grupos elegidos (nombre, formación, k) y por qué en una línea; avisos de solape de la consola; rutas de las dos imágenes; dudas de diseño; «Faltaba en el brief:».
