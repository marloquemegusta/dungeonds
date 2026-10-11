# Perfilado de tres rutas para el suelo FBX

## Objetivo

Reducir el coste de `F` sin atar el renderer al bake actual de 512×512. El generador lee `WORLD_W` y `WORLD_H`; la carga de tiles a VRAM se limita a un área móvil de 512×256 px y el resto del atlas/mapa queda como datos estáticos.

## Comparación

| Ruta | Medición intermedia | Resultado y límite |
| --- | --- | --- |
| BG bitmap 8bpp completo | 512×512 requiere 256 KiB de VRAM. A+B cubren el suelo inferior; queda C para actores inferiores. C no puede ser además BG de la pantalla superior, y el hardware de este toolchain no mapea D a Sub BG. Un mapa mayor también exige streaming por ventanas. | No se implementó como ruta final: el coste de VRAM sacrifica el fondo superior y no escala como bitmap completo. |
| BG tileado con ring map | DeSmuME intérprete, 240 frames: CPU medio 4.92 ms, máximo 5.86 ms; `F` 1.51 ms, `S` 0.80 ms, blits 1.34 ms; 239/240 frames a 60 FPS. Escenario de paseo PASS. | El coste de CPU ya no recorre ni copia el bitmap del mundo por frame; el trabajo depende de las celdas visibles y las filas/columnas que entran al viewport. |
| Pantalla superior a 30 Hz | DeSmuME intérprete, 240 frames: CPU medio 5.48 ms, máximo 6.44 ms; `F` 2.91 ms; 240/240 a 60 FPS. | Mantiene la simulación a 60 Hz, pero deja el fondo superior visualmente a 30 Hz y rindió peor que el ring map en este benchmark. |

La referencia física aportada por el usuario sigue siendo `20 FPS` con `F≈38 ms`; DeSmuME es una comparación interna y no valida la DSi. La ruta 1 es un cálculo de VRAM, no una medición de ROM.

## Generalidad

El generador ya no exige que el atlas entero quepa en los 128 KiB de una bank VRAM: la tabla estática puede crecer hasta el límite de IDs de 16 bits. El cache de VRAM conserva las piezas que se usan en el ring y cambia las celdas al desplazar cámara. Esto admite mundos más grandes con densidad local parecida; la DSi impone un límite inevitable al número de patrones únicos residentes a la vez.

## Validación visual pendiente

El escenario produce tres capturas y conserva movimiento, pero la subpantalla superior aparece negra en DeSmuME pese a que el mapa, tiles, paleta y enable de BG se observan en memoria. Por eso esta variante no se considera terminada ni se ha subido a la DSi. La pantalla inferior sí muestra el bake tileado y el HUD:

![Spawn del ring map: la captura muestra la pantalla superior negra](assets/option2-spawn.png)

![Movimiento por el pasillo FBX](assets/option2-walk.png)

## Archivos de perfil

- `assets/option2-profile.txt`
- `assets/option3-profile.txt`
- ROM de la ruta tileada: CRC `6A7EF7CC`.
- Requiere confirmar el resultado en DSi; el FTP no quedó disponible para una nueva subida en esta sesión.
