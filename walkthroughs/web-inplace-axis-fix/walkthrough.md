# In-place con la orientación real de la armadura

## Causa comprobada

El archivo comunicado por el usuario, `assets/characters/custom/mario_camisa_blanca.fbx`, tiene un clip `walk` de 2,2917 s. El lector FBX embebido conserva la armadura en Z-up y gira su grupo −90° alrededor de X para presentarla en Y-up. En `mixamorigHips.position`, el avance está en Y local (0,9766 → −152,0687) y la altura en Z local (50,9319 → 53,0721). Fijar X/Z local dejaba íntegro el avance y suprimía la oscilación vertical.

La explicación previa sobre RootNodeL no se confirmó al cargar Walking.fbx con el lector real; se corrigió ese registro.

## Corrección

Las posiciones de la pista se convierten mediante la matriz del padre de la raíz a los ejes de la escena. Se fijan X/Z de la escena, se conserva Y y se vuelven a convertir las posiciones a los ejes locales. La carga inicial y el cambio de la casilla pasan la jerarquía del modelo a esa operación. El cambio de casilla restaura la pose antes de leer la orientación de la armadura y reconstruye el mixer.

El estado de la casilla ya indica «Desactivada» cuando el bloqueo está apagado.

## Verificación con FBX reales

`tools/lab/inspect-offline-fbx.cjs` ejecuta directamente el FBXLoader, AnimationMixer, normalización y función in-place embebidos en el HTML. Solo simula la carga de imágenes; no utiliza WebGL ni automatiza la página file://. Comprueba 101 tiempos por cada una de las ocho direcciones, conserva la altura y verifica restauración exacta de todos los valores originales.

| FBX | Deriva anterior con X/Z local | Deriva corregida | Error vertical máximo |
| --- | ---: | ---: | ---: |
| Mario | 2,705293 | 8,67e−18 | 5,55e−16 |
| Walking | 1,73e−18 | 1,39e−17 | 0 |
| Skeleton | 3,47e−18 | 3,47e−18 | 0 |
| Run | 6,99e−18 | 6,99e−18 | 0 |

Valores en unidades de escena normalizadas. Tolerancia de aserciones: 1e−5. Los cuatro fixtures pasan, incluyendo la restauración del movimiento al desactivar. El script completo del HTML también pasa el análisis de sintaxis de Node.

Comando reproducible desde la raíz del repositorio:

```powershell
node tools/lab/inspect-offline-fbx.cjs assets/characters/custom/mario_camisa_blanca.fbx
```

Resultados numéricos guardados en [assets/results.json](assets/results.json). No se capturó una salida WebGL; la comprobación headless valida las transformaciones de la animación real.
