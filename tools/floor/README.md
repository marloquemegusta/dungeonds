# Suelo con relieve: notas del lab

El lab carga GLB mediante `tools/lab/glb_loader_minimal.js` y respeta `baseColorTexture` incrustada y `baseColorFactor`.
El parser lee `TEXCOORD_0`, crea `TextureLoader` y asigna `map` a `MeshStandardMaterial`; no lee `COLOR_0`.
Por eso el prototipo usa albedo PNG incrustado en GLB, UVs y material PBR, sin vertex colors.
El albedo se repite por recortes de UV de una fuente tileable; la altura desplaza una rejilla de geometría densa.
Los bordes de cada tile se fuerzan a Y=0 mediante una rampa de 4.5% del ancho, para unirlos sin saltos al repetir.
