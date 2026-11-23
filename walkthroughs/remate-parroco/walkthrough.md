# Walkthrough — Remate del Párroco: «derretirlo» (`claude/remate-parroco-f8ecfc`)

**Fecha:** 2026-11-23
**Diseño:** `DESIGN-ARPG.md` §5, línea del Párroco (decidido 2026-11-23)

## Qué se pidió

El remate (`L` sobre un Párroco tambaleante) con la idea «B · Derretirlo» elegida por el usuario. Tenía que diferenciarse del de los Exvotos pequeños, que parte al enemigo en dos.

## Versión aprobada (v4)

El héroe está de pie y erguido, sin pose de combate. El gesto es frío, con desdén: una ejecución, no una pelea. Extiende un solo brazo despacio, con la mano abierta, y le atraviesa el pecho; dentro, la mano se cierra como si agarrara el corazón. Del pecho sale un brillo cálido: núcleo marfil, halo ocre y 8 rayos cortos, en paleta `FX_SH_*`. El Párroco se derrite de abajo arriba: primero los pies y las piernas, mientras el torso baja entero con la mano dentro. Al final el torso se funde en el charco y el héroe saca la mano y se queda de pie. Restos: el charco, durante ~1 s.

- 40 fotogramas × 4 ticks (~2,7 s), celda 96×96, 8 direcciones.
- Ir de pie limita el alcance del brazo: el torso baja intacto ~0,17 m antes de fundirse. Si hiciera falta más recorrido, se ajusta con `PAR_D0` / `PAR_SMAX` en el script, añadiendo una flexión de rodillas.

## Rondas con el usuario

| Versión | Qué era | Qué pidió el usuario |
| :--- | :--- | :--- |
| v1 | Puñetazo, mecha y llama en la cabeza, derretido de arriba abajo | Dejar el puño dentro, derretir desde dentro con un brillo en el pecho, sin llama |
| v2 | Puño dentro, brillo en el pecho, derretido de arriba abajo | Que no sea un puñetazo sino alargar el brazo hacia el corazón; derretir de abajo arriba, conservando el torso |
| v3 | Mano al corazón, derretido de abajo arriba, pero con el héroe en guardia | Quitar la pose de boxeo: de pie, frío, una ejecución |
| v4 | De pie, un solo brazo, mano que se abre y se cierra | **Aprobada** |

## Tubería (todo en el lab rápido)

1. `tools/characters/ds_remate_parroco.py`: Blender sin ventana, un GLB por fotograma (`REMATE_GLB_DIR`). El derretido es una deformación de la malla ya posada, horneada en cada GLB. El brillo, los goterones y el charco son actores con topología fija. El brazo del héroe usa un IK de dos huesos hacia el pecho, y los pies del héroe no se desplazan (deriva 0).
2. `tools/lab/fast/export_scene_fast.cjs`, a 38 px/m.
3. `tools/generate_remate_sprites.py`: nuevo tipo `parroco` (`REMATE_KIND_PARROCO = 5`), que genera `nitrofiles/remate/parroco_d0..d7.bin`. El generador no conocía el Monaguillo ni el Bebé; ahora Ojo, Monaguillo y Bebé quedan congelados en `tools/remate_legacy.json`. Comprobado: sus tablas en `source/remate_sprites.c` son idénticas, solo con más relleno porque `REMATE_MAX_FRAMES` pasa de 38 a 40.
4. `source/remate.c`: `ENEMY_TYPE_PARROCO` → `REMATE_KIND_PARROCO`. El sandbox gana `SANDBOX_ENEMY_PARROCO`.

Los GLB y el paquete del lab (`assets/lab_out/`) son derivados y no se versionan. Para regenerar los bins: `PARROCO_GLB=<dir de GLB> python tools/generate_remate_sprites.py`. El color de la cera sale de la mediana de la textura base de los Exvotos (169,141,121), porque la textura del Párroco solo existe como puntero LFS.

## Evidencia (de la ROM, 4x NEAREST, 50 ms)

- Aprobada: [`assets/parroco_remate_rom_4x_v4.gif`](assets/parroco_remate_rom_4x_v4.gif), de perfil [`d2`](assets/parroco_remate_d2_4x_v4.gif) y en diagonal [`d3`](assets/parroco_remate_d3_4x_v4.gif), y fases clave en [`assets/parroco_remate_fases_4x_v4.png`](assets/parroco_remate_fases_4x_v4.png).
- Versiones anteriores, con sufijos `_v2`, `_v3` y sin sufijo (v1).
- Los GIF de la ROM acaban un fotograma antes de que aparezca el botín del enemigo.

## Verificación

- Build `remate-sandbox`: PASS, 0 avisos nuevos (los 2 avisos de `main.c` ya existían). Variante por defecto: 0 avisos.
- Escenarios en `remate-sandbox`: `remate_transicion_parroco_cerca` (nuevo), `exvoto_cerca`, `exvoto_oeste`, `cireneo_norte` y `ojo_cerca` PASS.
- Sin tests de host ni medición `perf` en la DS. El remate lee un fotograma por vez desde NitroFS, como los demás; el bin mayor es de 196,7 KB.

## Pendiente

- Medir en la DS antes de mergear (regla 6).
- Si el Párroco cae al muñeco de reserva (`CHAR_EXVOTO`), el primer fotograma del remate cambia de modelo.
- Al juntarlo con la rama de la Súper Monja, `SANDBOX_ENEMY_PARROCO = 6` y el número de tipos de remate pueden chocar.
- No hay merge ni push.
