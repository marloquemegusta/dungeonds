# ARPG: ROM de prueba de sonidos

Variante `prueba-sonidos` (`ARPG_LAB`, `SOUND_TEST`, `SKIP_TITLE`, `ARPG_ALL_UNLOCKED`): sala de pruebas para escuchar cada sonido del ARPG en su contexto y apuntar cuáles chirrían. No cambia ningún sonido del juego.

- **Menú (SELECT):** página «Escenas» (escena + invulnerable + ayuda), cuatro páginas de catálogo con todos los `SND_*` (archivo y origen: `K·` banco gratuito Kenney, `IA·` ElevenLabs; A repite) y «Banco gratuito» con los 31 `lab_*`.
- **Escenas:** 0 mapa normal · 1 Remates · 2 Hechizos (Rayo, Glifo) · 3 Ojos · 4 Cireneos · 5 Monja cura (curación simulada: la oración está desconectada en el ARPG) · 6 Monaguillos · 7 Campanero (tañido, toque, cristal del Glifo).
- Arreglo del lab, válido fuera de la variante: escuchar una voz de jefe desde el menú ya suena (antes se pedía un efecto no cargado).
- Con `SOUND_TEST` el héroe invulnerable sigue sonando al recibir daño, para poder oír «Héroe herido».

Verificado: compila limpia sin avisos (`prueba-sonidos`, por defecto y `arpg-lab`); escenario de evidencia `scenarios/prueba_sonidos.json` (`suite:false`). El audio no se ha oído en el emulador: la escucha es en la DS.

Hoja para marcar (móvil): https://claude.ai/artifact/BCUZrgcGjshczPMPAn7WLK

| | |
|---|---|
| ![Catálogo Héroe](assets/catalogo_heroe.png) | ![Escenas](assets/catalogo_escenas.png) |
| ![Remates](assets/escena1_tambalea.png) | ![Campanero](assets/escena7_toque.png) |

Resultado: el usuario la escuchó en la DS y marcó en la hoja lo que chirría; la lista está en `STATUS-ARPG.md` («Pendiente», punto 5). MDs: `STATUS-ARPG.md`, `STATUS-ARCHIVE.md`, `TECHNICAL.md` §5.3c y `walkthroughs/README.md`.

## Ronda 2 y 3: sonidos definitivos (2026-11-24)

El usuario eligió en la DS, entre candidatos de ElevenLabs (`assets/sfx/raw/cand/`, no versionados; las fuentes elegidas están en `assets/sfx/raw/<nombre>.mp3`):

- Glifo: `glifo_grieta` (grieta) y `glifo_detonacion`. Orbe: `pickup_orb` (B). Monaguillo: `monaguillo_emerge` (C). Cireneo contra el muro: `cireneo_wall` (C, golpe grave, volumen a 255).
- Remates, un sonido por ejecución y varias pistas cuando hay varios tiempos: `remate_cera` (Exvoto, Monaguillo, Bebé; la variante «raja lenta» sale de la A con atempo 0,7), `remate_tiron` + `remate_caida` (Súper Monja), `remate_viga` (Cireneo), `remate_forcejeo` + `remate_ojo` (Ojo), `remate_mano` + `remate_derretir` (Párroco). Se retira `remate_exec`.
- Mezcla: tambaleo con retraso tras el puñetazo, el Rayo ya no reproduce el impacto de enemigo, y la campana del Campanero suena al alzarse.
- La escena 1 de la variante tiene 7 unidades (con la Súper Monja) y `ROOM_POOL_BYTES=1760000` solo en esta variante; la escena 4 alarga la carga del Cireneo.

| | |
|---|---|
| ![Escena 1](assets/r3_escena1.png) | ![Catálogo de remates](assets/r3_catalogo_remates.png) |

Pendiente: sonido de premio propio para la reliquia. MDs: `STATUS-ARPG.md`, `STATUS-ARCHIVE.md`, `assets/MANIFEST.md`, `TECHNICAL.md` §5.3c, `DESIGN-ARPG.md`.
