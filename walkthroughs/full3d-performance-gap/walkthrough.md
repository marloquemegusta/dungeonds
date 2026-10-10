# Sesi?n 24: Recuperar el rendimiento del renderer FBX

## Diagn?stico

Compar? el renderer modular (`d87b0e2`) y el renderer FBX en DeSmuME 0.9.14 con la misma build BlocksDS, la misma secuencia determinista y 240 frames.

| Ruta | CPU medio | CPU m?ximo | Frames a 60 FPS | Suelo | Objetos/oclusiones |
| --- | ---: | ---: | ---: | ---: | ---: |
| Modular, fondo BG ring-map | 8.36 ms (49.55%) | 9.01 ms (53%) | 240/240 | 29.1 ?s | 2.20 ms |
| FBX inicial, bitmap + replay de spans | 51.53 ms (307.80%) | 64.14 ms (383%) | 14/240 | 10.92 ms | 39.32 ms |
| FBX final, profundidad precalculada + DMA | 8.60 ms (50.97%) | 9.55 ms (57%) | 239/240 | 5.84 ms | 1.45 ms |

La ca?da no proven?a del movimiento ni de la colisi?n. El renderer FBX copiaba por CPU dos ventanas de 256?192 por frame y volv?a a recorrer 16,908 spans de oclusi?n al componer las entidades. El 90.7% de esos spans med?a s?lo 1?4 p?xeles. La ruta modular, en cambio, manten?a el fondo en un ring map de BG hardware y actualizaba ?nicamente los bordes expuestos.

## Plan ejecutado

1. Med? ambas rutas con escenario y herramienta id?nticos para localizar los costes dominantes.
2. Prob? el fast path de spans cortos. Baj? el coste de objetos/oclusiones de 39.32 a 34.05 ms, pero no recuper? los 60 FPS.
3. Reemplac? el replay por una tabla de profundidad por p?xel generada una vez desde los mismos spans. Al dibujar cada p?xel opaco de una entidad, consulto esa profundidad con el mismo orden y comparaci?n que el compositor original.
4. Copi? cada fila del fondo con DMA halfword en vez de 384 llamadas de `memcpy` por pantalla/frame.
5. Repet? el benchmark y compar? capturas de la ROM previa y la optimizada, alineadas por estado de juego.

## Resultado

| Medida FBX | Antes | Final |
| --- | ---: | ---: |
| CPU medio | 51.53 ms | 8.60 ms |
| Objetos/oclusiones | 39.32 ms | 1.45 ms |
| Copia de suelo | 10.92 ms | 5.84 ms |
| Frames a 60 FPS | 14/240 | 239/240 |

La captura en reposo y la captura tras el mismo movimiento son id?nticas p?xel a p?xel (0 p?xeles distintos en ambas). La posici?n del jugador, c?mara, enemigos activos y contador de navegaci?n tambi?n coinciden en los puntos comparados. No se cambi? movimiento, colisi?n, orden de profundidad ni reglas de juego.

La tabla agrega 512 KiB de BSS; el binario sigue dentro del presupuesto de RAM de DS cl?sica. La medici?n fue en DeSmuME, no en hardware f?sico. El resultado recupera pr?cticamente el rendimiento modular, con un frame de 240 por debajo de 60 FPS; por ello no afirmo un bloqueo perfecto a 60 FPS.

## Verificaci?n

- Build BlocksDS limpia y ROM `D0C11952`.
- Pruebas host y escenarios FBX pasan.
- Benchmark de 240 frames: 239/240 a 60 FPS, CPU medio 8.60 ms.
- Comparaci?n visual alineada: 0 p?xeles distintos en reposo y en movimiento.
- Evidencia: [`assets/perf-modular-240.txt`](assets/perf-modular-240.txt), [`assets/perf-full3d-240.txt`](assets/perf-full3d-240.txt), [`assets/perf-optimized-240.txt`](assets/perf-optimized-240.txt), [`assets/perf-final-240.txt`](assets/perf-final-240.txt).
