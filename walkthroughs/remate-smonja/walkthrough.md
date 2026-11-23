# Walkthrough — Remate de la Súper Monja araña («monjaraña»)

**Fecha:** 2026-11-23
**Rama:** `claude/remate-smonja-27d615` (sobre `claude/arpg-exvoto-ramas-a622a1`)
**Diseño:** `DESIGN-ARPG.md` §5, Súper Monja, «Remate»; reglas comunes en `DESIGN.md` §6.13.8

## Qué se pidió

La idea del usuario para el remate de la Súper Monja en forma araña: el héroe le agarra la cabeza y se la arranca, y el
cuerpo cae inerte y espatarrado. Se escribió en el diseño antes de programarlo (regla 9).

## Rondas

1. **Primera versión:** dos variantes de la caída de la cabeza, «a sus pies» y «lanzada lejos». La lanzada lejos caía
   detrás del cuerpo y se perdía sobre el suelo oscuro. El usuario aprobó la primera, pero pidió un arranque más
   exagerado, para que se leyera mejor.
2. **A/B del tirón:** la A es el tirón corto. En la **B** el héroe se echa atrás girando el torso y se lleva la cabeza
   en un arco amplio, unas 1,4 veces el recorrido de la A. El cuello se estira antes de soltarse, salta el doble de cera
   y el cuerpo rebota hacia atrás antes de caer. **El usuario eligió la B.**

## Secuencia (B, 36 fotogramas a 4 ticks ≈ 2,4 s, celda 160×160)

Fotogramas en orden: agarre con los brazos estirados → tirón hacia atrás con el cuerpo araña arrastrado → arranque en
el pico del tirón (estirón del cuello y gotas de cera oscura) → la cabeza sube en arco y cae junto a los pies del
héroe → el cuerpo rebota y se desploma boca arriba, espatarrado → restos (fotograma extra sin héroe: cuerpo y cabeza).

## Cómo se hace

- `tools/characters/ds_remate_smonja.py` (Blender): escena del héroe con la pose araña de `super_monja_arana.py`. La
  variable `SM_VAR=A|B` elige la variante; por defecto, la B. Los modelos fuente se leen de la carpeta principal
  (`SM_MODEL_ROOT`), porque en el worktree son punteros LFS.
- Lab rápido: `tools/lab/fast/export_scene_fast.cjs --ppm 38 --resolution 160`.
- `tools/pack_remate_smonja.py`: escribe `nitrofiles/remate/smonja_d0..d7.bin` y añade o actualiza
  `REMATE_KIND_SMONJA` en las tablas. Usa un empaquetador propio porque `tools/generate_remate_sprites.py` solo conoce
  3 de los 5 tipos actuales: regenerar con él borraría el Monaguillo y el Bebé.
- Todo de una vez: `bash tools/characters/regen_remate_smonja.sh`.
- `source/remate.c`: `ENEMY_TYPE_MONJA` usa el remate `smonja`.

## Evidencia (ROM real, 4x NEAREST, 60 ms por fotograma)

- A | B sincronizados, entrando desde el oeste: [`assets/smonja_remate_AB_oeste_4x.gif`](assets/smonja_remate_AB_oeste_4x.gif)
- B, entrando desde el oeste: [`assets/smonja_remate_rom_oeste_B_4x.gif`](assets/smonja_remate_rom_oeste_B_4x.gif) y su tira, [`assets/smonja_remate_rom_oeste_B_tira_4x.png`](assets/smonja_remate_rom_oeste_B_tira_4x.png)
- B, entrando desde el sur: [`assets/smonja_remate_rom_sur_B_4x.gif`](assets/smonja_remate_rom_sur_B_4x.gif)
- Ronda 1 (cabeza lanzada lejos, descartada): [`assets/smonja_remate_rom_oeste_lejos_4x.gif`](assets/smonja_remate_rom_oeste_lejos_4x.gif)
- Página que vio el usuario: [`assets/smonja_remate_ronda1.html`](assets/smonja_remate_ronda1.html)

El paquete del lab (`assets/lab_out/`, ~86 MB) es derivado y no se versiona; se regenera con el script.

## Verificación

- Build `arpg-lab`: 0 avisos. Build `remate-sandbox`: 2 avisos de funciones sin usar en `main.c`, que ya estaban antes.
- Escenarios `scenarios/remate_transicion_smonja.json` (oeste) y `remate_transicion_smonja_sur.json`: PASS. Van sobre
  `arpg-lab`, porque el `remate-sandbox` no sabe crear a la Súper Monja.
- Memoria: los buffers de streaming del remate crecen ≈6 KB (`REMATE_PIX_BYTES` 23552, `REMATE_MASK_BYTES` 3072) por
  la celda de 160. Bins: ≈2,46 MB en NitroFS.

## Pendiente

- Medir `perf` en la DS durante el remate.
- Volver a pasar `remate_transicion_ojo_cerca`. El código compartido no cambia, pero los buffers sí crecen.
- En los fotogramas 6–9 del tirón, las manos quedan a 15–25 cm de la cabeza. No se nota en el GIF.
- `tools/generate_remate_sprites.py` debería conocer los 6 tipos de remate.

MDs: `DESIGN-ARPG.md` (remate), `STATUS-ARPG.md` y `STATUS-ARCHIVE.md`, y este índice. Al llevar la rama a
`proto/arpg`, sincronizar los MDs con `main`.
