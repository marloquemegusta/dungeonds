# Sesión 18: Perfil de rendimiento de Mario frente al héroe

## Método

- Blender 5.2.1 LTS; Windows.
- Dos renders por asset, alternados, con los mismos parámetros: 48×48 px, 12 muestras, outline, 8 direcciones × 8 frames (64 imágenes).
- Tiempos de render e importación medidos dentro del worker Blender; tiempo total medido desde `execute_render_job`.
- Los tiempos de la tabla son medianas de dos ejecuciones; por el tamaño de muestra sirven para localizar diferencias grandes, no para microbenchmark preciso.

## Resultados

| Métrica | Héroe Nigromante | Mario | Diferencia |
|---|---:|---:|---:|
| FBX | 19,86 MB | 14,08 MB | Mario −29 % |
| Vértices | 5.851 | 9.701 | Mario +66 % |
| Polígonos | 6.994 | 19.390 | Mario 2,77× |
| Huesos | 37 | 65 | Mario +76 % |
| Imágenes/materiales | 2/1 | 6/1 | Mario +4 imágenes |
| Importación FBX | 0,397 s | 0,575 s | +0,178 s |
| Setup de escena y bounds animados | 0,108 s | 0,161 s | +0,053 s |
| Render de 64 frames | 2,190 s | 2,466 s | +0,276 s |
| Render medio por frame | 0,0342 s | 0,0385 s | +13 % |
| Worker Blender completo | 5,743 s | 6,305 s | +0,562 s |
| Job completo, incluido postproceso/GIF | 6,152 s | 6,608 s | +0,456 s (+7,4 %) |

El primer frame cuesta ~0,33 s en ambos assets; los 63 restantes rondan 0,03–0,04 s. Ese primer frame no explica una diferencia grande entre los modelos.

## Conclusión

Mario sí tiene más geometría, huesos e imágenes, y cada frame cuesta alrededor de un 13 % más. En el Shader Lab actual, sin búsqueda recursiva de texturas, el job completo solo fue un 7,4 % más lento que el del héroe: **6,6 s frente a 6,2 s**. La importación FBX añade apenas **0,18 s**; el retraso de cientos de segundos que se medía antes procedía de la búsqueda recursiva de imágenes desde rutas obsoletas.

Si la interfaz aún tarda mucho más que estos ~6–7 s, la demora estaría fuera del render job medido o usando otros parámetros; conviene medir una ejecución desde la interfaz con su resolución, muestras y acción exactas.
