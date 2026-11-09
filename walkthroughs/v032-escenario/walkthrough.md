# 0.3.2 — Catálogo visual del escenario (catedral)

Elige por letra o número. Todas las imágenes están en `assets/`. Las capturas "ROM" son de la ROM real (escenario `strip_cathedral_look`, build 0 warnings).

## 1. Suelos — [`cat_suelos.png`](assets/cat_suelos.png)
Misma escena (marine, banco, columna, vela, con sombra) sobre cada suelo.
- **1 rombos** — damero de rombos 3D, oscuro. *Tu favorito hasta ahora.*
- **2 rombos_b** — igual, algo más claro y con más contraste.
- **3 rombos_h** — rombos con tono más cálido.
- **4 rombos_h_b** — cálido y más claro.
- **5–8 losas_3d (+ _b, _h, _h_b)** — losas rectangulares de relieve suave, casi sin dibujo.
- **9 rombos_tripo** — damero con tus losas de Tripo (casi lisas, 2 especiales por bloque), poco contraste.
- **10 rombos_tripo_b** — igual con más contraste entre las dos piedras.

Comparativa antigua de los rombos: [`rombos_4_variantes.png`](assets/rombos_4_variantes.png).

## 2. Lápidas — [`cat_lapidas.png`](assets/cat_lapidas.png)
A cruz horizontal · B cruz vertical · C caballero horizontal · D caballero vertical · E cruz v2 horizontal · F cruz v2 vertical · G caballero v2 horizontal · H caballero v2 vertical. Todas a ras de suelo (sin sombra), unos 4 m, con el marine para escala.
**Límite:** la ROM tiene un tope de 1024 tiles; con un suelo y las piezas actuales solo caben 1 o 2 lápidas. El resto solo se ve aquí.

## 3. Sombras de las piezas — [`cat_sombras.png`](assets/cat_sombras.png)
Cada pieza sin sombra (izquierda) y con sombra (derecha). Recomendación: con sombra, alineada con la luz del marine.

## 4. Personajes — [`cat_personajes.png`](assets/cat_personajes.png)
Con contorno (como ahora en la ROM) frente a sin contorno (luz neutra).

## 5. Composiciones completas en la ROM real
| Opción | Suelo | Personaje | Inicio | Subida |
|---|---|---|---|---|
| **P** | rombos | con contorno | [img](assets/rom_rombos_conContorno_inicio.png) | [img](assets/rom_rombos_conContorno_subida.png) |
| **Q** | rombos | sin contorno | [img](assets/rom_rombos_sinContorno_inicio.png) | [img](assets/rom_rombos_sinContorno_subida.png) |
| **R** | rombos_tripo | con contorno | [img](assets/rom_tripo_conContorno_inicio.png) | [img](assets/rom_tripo_conContorno_subida.png) |
| **S** | rombos_tripo | sin contorno | [img](assets/rom_tripo_sinContorno_inicio.png) | [img](assets/rom_tripo_sinContorno_subida.png) |

Presupuesto de tiles (máx. 1024): P/Q 994 (6 piezas + 2 lápidas cruz v2); R/S 981 (suelo de Tripo es más caro, así que sin banco volcado y con una sola lápida).
No se ha medido en la DS (solo emulador); antes de elegir en firme falta la prueba `PERF_PROFILE`.

## Qué decidir
1. Suelo (1–10). 2. Qué lápidas (A–H, caben 1–2). 3. Sombras sí/no. 4. Personajes con o sin contorno.

## Notas técnicas
- Damero de Tripo: `tools/floor/rombos_tripo.py`; la piedra B es losa_a recoloreada (ΔL* 10,3 / 15,8). Con los mismos props, `rombos_tripo` da 1120 tiles y no cabe; hay que quitar piezas.
- Hojas: `tools/catalogo/*.py` (reejecutables). Biblia §6 corregida. Plan de reordenado de assets: [`REORDEN_ASSETS.md`](REORDEN_ASSETS.md) (sin ejecutar).
- Limpieza manual pendiente: mover del inbox las lápidas v2 y las losas de Tripo a `assets/models/environment/cathedral/tripo/` y borrar los 7 duplicados.
- Estado de la ROM del worktree: suelo rombos_tripo, sprites sin contorno (último build).

## 6. Decisiones tomadas (2026-11-08) y estado
- **Elegido:** personajes **sin contorno**; suelo **Tripo A** (`rombos_tripo`).
- **Sombras:** la luz real es elev 55°, azimut 30°. Las sombras de las piezas se alinearon con la del marine ([`sombras_alineadas.png`](assets/sombras_alineadas.png)); copia anterior en `props/render_backup_sombra/`.
- **Lápidas de suelo:** sustituyen losas, ocupan rombos enteros, cluster de un tono y junta oscura fina (1 px, color suave). Prototipo: [`cat_lapidas_cluster.png`](assets/cat_lapidas_cluster.png). En la ROM real (variante `lapidas`): `rom_lapida_*.png`.
- **Tope de tiles (1024):** real. Las 8 lápidas gastan ~379 tiles; en la ROM van 5 (cruz v2 y caballero v2 horizontales, cruz y caballero horizontales, cruz v2 vertical): 882/1024.
- **Baker:** ya no cuenta tiles huérfanos (antes 880 con el damero antiguo, ahora 565).
- **Pendiente:** medir en la DS (`PERF_PROFILE`); endurecer los escenarios `strip_*` (su captura de inicio sale antes del arranque); decidir qué lápidas verticales más caben.

### Probado, sin decidir
- **Lápida hundida (composición 3D):** prototipo `lapida3d_cruz2_h` (128×96 px, 192 tiles únicos, hundida 8 cm, costura 3,56/255 con el damero; [`lapida3d_proto_small.png`](assets/lapida3d_proto_small.png)). Quitado el foso, la lápida se lee poco contra la placa y cuesta más del doble de tiles. **El usuario dice que no quedó bien: hundida o a ras sigue sin decidir.** Variante elevada en `render/lapida3d_cruz2_h_elevada/`. No está en el baker ni en la ROM.
- **Ahorro de tiles (sin elegir):** menos fases de las piezas, quitar relicario o banco_volcado, suelo más simple, solo lápidas v2.
- **Reorden de `assets/`:** plan en `REORDEN_ASSETS.md`, nada movido. Limpieza manual del inbox pendiente (7 zips duplicados; mover lápidas v2 y losas Tripo a `assets/models/environment/cathedral/tripo/`).
- **Sin hacer:** medición en la DS con `PERF_PROFILE`.

## 7. Solución Definitiva de Lápidas — Pipeline Unificado Shader Lab (2026-11-09)
Se resuelve el diseño y pipeline de integración de lápidas en el suelo de la catedral:
- **Pipeline 100% unificado en Three.js Shader Lab (`tools/lab/export_map_package_headless.cjs`)**: se eliminó el renderizado aislado de Cycles; Blender actúa exclusivamente como ensamblador 3D exportando a GLB (`build_lapidas_lab_blender.py`).
- **La lápida ES la losa**: sustitución exacta de teselas completas en el damero con junta de mortero oficial (`JOINT = 0.026 m`). CERO outlines 2D y CERO cajeados oscuros.
- **Modelos Tripo v2 con relieve realzado (12 cm)**: la geometría 3D completa de la armadura, espada y cruz capta la luz y sombras de contacto de forma nítida.
- **Cuantización nativa BGR555**: 15 bits de precisión de color Nintendo DS sin aplastar el rango dinámico.
- **Evidencia visual**: lámina maestra [`cat_lapidas_lab_unified.png`](assets/cat_lapidas_lab_unified.png) comparando:
  * Vía A ($3 \times 2$ teselas = $80 \times 40\text{ px}$): Cruz y Caballero yacente a 45°.
  * Vía B ($3 \times 3$ teselas = $96 \times 48\text{ px}$): Cruz y Caballero horizontales en pantalla inscritos en rombo.

