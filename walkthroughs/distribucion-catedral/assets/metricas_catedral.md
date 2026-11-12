# Metricas de distribucion (vista previa Python)

| modo | ventana (bandas) | huella % suelo util | pasillo central min | paso lateral min |
| :--- | :--- | ---: | :---: | :---: |
| catedral | bandas 0-11 (12) | 9.19 | 56 px (banda 8) | 56 px (banda 0) |
| catedral | bandas 12-23 (12) | 6.42 | 56 px (banda 17) | 56 px (banda 16) |
| catedral | bandas 24-35 (12) | 9.00 | 56 px (banda 25) | 48 px (banda 32) |
| catedral | bandas 36-47 (12) | 6.22 | 56 px (banda 41) | 56 px (banda 42) |
| catedral | bandas 48-59 (12) | 7.98 | 56 px (banda 49) | 56 px (banda 48) |
| catedral | bandas 60-63 (4) | 2.64 | 148 px (banda 62) | 160 px (banda 62) |

- Huella total (64 bandas): 7.44 % del suelo util.
- Peor ventana de 33x25 tiles: **351** (< 440).
- Peor oclusion de 16 bandas: **15624** runs (< 32768).
- Columnas por estado: entera=49 (`columna_entera`), rota=35 (`columna`), caida=10 (hueco).
- Bancos: entero=119 (77.8 %), roto=34 (22.2 %).
- Piezas por tipo: banco_entero=119, banco_roto=34, banco_volcado=3, lapida_cruz_h=3, relicario=14, sacos=18, santo=28, vela=65.
