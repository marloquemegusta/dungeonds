# Sesión 24: Por qué el render FBX pierde los 60 FPS

## Diagnóstico controlado

Comparé el commit modular (`d87b0e2`) y la rama FBX actual usando la misma build BlocksDS, DeSmuME 0.9.14, script de botones determinista y 240 frames. Los registros están en `assets/perf-modular-240.txt` y `assets/perf-full3d-240.txt`.

| Ruta | CPU medio | CPU máximo | Frames a 60 FPS | Suelo | Objetos/oclusiones |
| --- | ---: | ---: | ---: | ---: | ---: |
| Modular, fondo BG ring-map | 8.36 ms (49.55%) | 9.01 ms (53%) | 240/240 | 29.1 µs | 2.20 ms |
| FBX, bitmap 512×512 + spans | 51.53 ms (307.80%) | 64.14 ms (383%) | 14/240 | 10.92 ms | 39.32 ms |

El FBX cuesta 43.16 ms adicionales por frame, unas 6.16 veces el CPU total de la ruta modular. La pantalla inferior consume 43.91 ms frente a 5.11 ms en la ruta modular.

## Causa

El modelo FBX se hornea a una imagen RGB555 de 512×512. Cada frame se copian por software las dos ventanas visibles de 256×192: 192 KiB/frame, medidos ahora en 10.92 ms. El suelo modular está en un ring map de BG hardware; sólo se actualizan los bordes expuestos y su streaming medía ~29 µs/frame.

Además, el compositor de profundidad FBX mezcla 16,908 spans horneados con las entidades en CPU. El coste de renderizar objetos y oclusiones es 39.32 ms; este trabajo explica la mayor parte de la regresión. No es el movimiento ni la colisión: no hace falta reducir precisión ni alterar el gameplay para apuntar a estos costes.

## Plan ejecutado dentro del límite de 40 minutos

1. Perfil A/B de 240 frames con la misma ROM/toolchain/DeSmuME, para separar suelo y spans.
2. Conté 16,908 spans en el bake: 90.7% miden 1–4 píxeles. Evité `memcpy` en esos tamaños con copias halfword explícitas; bytes y orden de composición son idénticos.
3. Repetí el mismo benchmark y conservé el fast path sólo para tamaños cuyo resultado fue medible.

## Resultado y validación

| Medida FBX | Antes | Después | Cambio |
| --- | ---: | ---: | ---: |
| CPU medio | 51.53 ms | 45.84 ms | −11.0% |
| Objetos/oclusiones | 39.32 ms | 34.05 ms | −13.4% |
| Frames a 60 FPS | 14/240 | 13/240 | Sigue por debajo del objetivo |

El cambio acelera la CPU pero **no arregla todavía la caída a 60 FPS**. Se mantuvo porque copia exactamente los mismos píxeles y baja de forma consistente el coste de composición. El intento de extender el fast path a 5–8 píxeles y la copia alineada de 32 bits no mejoraron el resultado y se descartaron. El gameplay, la profundidad, la colisión y la resolución visual no cambian.

Build BlocksDS, 27 pruebas host y benchmark DeSmuME PASS. No se verificó en hardware DS.

## Siguiente fase necesaria

La copia del bitmap sigue costando ~10.5 ms y el compositor ~34 ms, frente al presupuesto de 16.7 ms. Para recuperar 60 FPS hace falta una segunda fase: sustituir el replay global de spans por oclusión espacial consultada sólo sobre píxeles de entidades, o rehacer el fondo FBX como BG hardware por chunks. Medir VRAM/RAM y comparar capturas píxel a píxel antes de aceptar esa re-arquitectura; no recortar precisión de profundidad ni cambiar reglas del gameplay.

## Evidencia

- Benchmark modular: [`assets/perf-modular-240.txt`](assets/perf-modular-240.txt)
- Benchmark FBX antes del fast path: [`assets/perf-full3d-240.txt`](assets/perf-full3d-240.txt)
- Benchmark FBX tras la optimización: [`assets/perf-optimized-240.txt`](assets/perf-optimized-240.txt)