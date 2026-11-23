# STATUS-ARPG.md - Estado del prototipo ARPG

Estado para retomar la protodemo ARPG (código en la rama `proto/arpg`) y sus entregas recientes (más nueva primero). Este archivo es idéntico en `main` y `proto/arpg`; los enlaces a walkthroughs solo resuelven en `proto/arpg`. Diseño en `DESIGN-ARPG.md`; detalle técnico en `TECHNICAL.md` §5. El estado del juego de `main` (Acto I por encuentros) está en `STATUS.md`.

## Estado actual (2026-11-22)

- **Hecho e integrado:** bucle campamento ↔ catedral, XP directa al matar y subida de nivel al dormir, inventario táctil estilo *Diablo II / Sacred* con giros 3D desde NitroFS, reliquias de la protodemo (2 auras de Rayo, 1 de Ejecución reservando la 2.ª para Levantar, 2 de Pecho y 3 Legendarias) conectadas con su `mech_val` y unidades explícitas al combate real, escalado Nivel vs. Rareza con bloqueo `Req. Nv. X` al equipar y drops de nivel fijo por ala/escalón, y dirección de arte documentada para los 3 escalones del Exvoto como etapas de corrupción biológica (`DESIGN-ARPG.md` §5).
- **Pendiente para cerrar la protodemo:**
  1. **Glifo:** hecho y probado en la DS (`glifo-diseno/`, `glifo-pulido/`). Falta el log `perf` con 3 glifos y salas llenas; enemigos apilados en el Redil aceptados.
  2. **Zona 1:** mapa fijo de 12 salas, fundidos, persistencia y mapa con SELECT hechos (`arpg-mapa/`). Falta: llave, rejas de capilla, premios por sala, dificultades (Pesadilla, Infierno), atajo, viaje entre altares y santuarios.
  3. **Campamento nocturno:** hecho (ver entrega). Queda decidir en qué se gasta la cera (hoy solo se acumula) y medir `perf` en la DS.
  4. **Interfaz:** nombre definitivo del juego (el título dice EXVOTION, provisional).
  5. **Sonidos definitivos:** elegir y sustituir los efectos de sonido (SFX) actuales, que son provisionales, por los definitivos (los gratuitos `lab_*` gustaban más de partida). Escuchados en la DS con la variante `prueba-sonidos` (2026-11-23, [`walkthrough`](walkthroughs/arpg-prueba-sonidos/walkthrough.md)). Chirrían:
     - `SND_REMATE_EXEC` (`remate_exec`): uno solo para todos los remates y no se entiende qué representa.
     - `SND_PICKUP_ORB` (`pickup_orb`): se oye poco; recoger una reliquia debe sonar a premio.
     - `SND_GLIFO_CRACK` (`lab_creak`, gratuito): suena cómico, a trompetilla de payaso.
     - `SND_GLIFO_DETONATE` (`lab_mining0`, gratuito): flojo y cutre.
     - `SND_MONAGUILLO_EMERGE` (`monaguillo_emerge`): correcto, pero no se entiende qué representa.
     - Mezcla: el aviso de tambaleo tapa `SND_PUNCH_HIT` cuando el primer golpe ya tambalea, y el disparo del Rayo tapa `SND_ENEMY_HIT` (quitarlo o dar al Rayo su propio impacto).
     - Por revisar: `SND_CIRENEO_WALL` no sonó en la escena de prueba (sin confirmar si es la escena o el juego).
     - Valen todos los demás, incluido `player_hurt`. Ningún candidato del banco gratuito gustó como sustituto.
  6. **Campanero (zona 2):** equilibrar el encuentro y rediseñar su sala (`DESIGN-ARPG.md` §9).
  7. **Validación en DS:** medición `perf` en hardware (campamento nocturno y salas con ~24 enemigos) y prueba de guardado en tarjeta real (`dungeonds_arpg.sav`).

**Fallos conocidos propios de la rama** (los comunes, en `STATUS.md`):
- `test_cathedral_kit` falla en `proto/arpg` (23 piezas en el baker frente a 19 en el enum del header; sin diagnosticar, no lo toca el campamento).

## Entregas recientes (más nueva primero)

- **ROM de prueba de sonidos (`claude/arpg-prueba-sonidos-723ae1`, 2026-11-23, en `proto/arpg`):** variante `prueba-sonidos`: 7 escenas elegibles desde el menú (SELECT) que disparan cada grupo de sonidos en su contexto (remates, Rayo y Glifo, Ojos, Cireneos, Monja, Monaguillos, Campanero) y catálogo con cada `SND_*`, su archivo y su origen (banco gratuito o IA) más los 31 `lab_*`. Escuchada en la DS por el usuario; la lista de lo que chirría está en «Pendiente», punto 5. Build 0 avisos; no se sustituyó ningún sonido. [`walkthrough`](walkthroughs/arpg-prueba-sonidos/walkthrough.md).
- **Campamento nocturno cerrado (`claude/arpg-campamento-19aed8`, 2026-11-23, sobre `proto/arpg`):** muros del campamento = muros de la catedral con grietas e hiedra; la mesa es el Crisol de desguace (bolsa sin engarces; el arcón queda sin Crisol); los objetos utilizables respiran un halo cálido y el portón brilla en el umbral. **Alijo del arcón:** 16 huecos para reliquias, guardado en la partida (v6; los v5 se leen). Build 0 avisos; escenarios `camp_foco_crisol` y `camp_alijo` (evidencia). **Sin hacer:** medir `perf` en la DS; pociones/gasto de cera (decidido: solo desguace). [`walkthrough`](walkthroughs/arpg-campamento/walkthrough.md).
- **Título e inventario (`claude/arpg-acabado-0baf54`, 2026-11-23, sobre `proto/arpg`):** pantalla de título con el nombre provisional EXVOTION y una vela que parpadea, las dos pantallas sobre el mismo fondo oscuro; el inventario pasa a Palatino 10 (fuente propia; el resto sigue en 11). Builds 0 avisos; `arpg_titulo` y `arpg_menus_inicio_final` PASS (capturas). Sonidos aplazados a una ROM de prueba. [`walkthrough`](walkthroughs/arpg-acabado/walkthrough.md)
- **Depósito de sala: reparto RAM / cartucho (`perf/ram-por-sala`, 2026-11-23, en `proto/arpg`):** los enemigos salen de la RAM fija y se cargan por sala en la pantalla de carga (depósito de 1,70 MB; la sala más cara, la del Campanero, 1,63 MB); sombras a 1 bpp en todos los personajes (Campanero 1,57 → 1,12 MB); Párroco, Súper Monja y Campanero ya no leen del cartucho en combate salvo respaldo. Regla para todo contenido nuevo en `TECHNICAL.md` §3.3.1. Builds 0 avisos nuevos, barrido de 12 salas sin cargas imprevistas, escenarios y tests PASS; **sin medir en la DS**. [`walkthrough`](walkthroughs/ram-por-sala/walkthrough.md).
- **Exvotos de escalón 3 (`claude/arpg-exvoto-ramas-a622a1`, 2026-11-23, en `proto/arpg`):** Súper Monja araña emboscada (embestida que persigue, esquiva el Glifo) con aura de posesión sobre Monja de cera y Monaguillo (se levantan al quedar tambaleantes); Párroco inmune al Rayo (destello, chispas, «0»); guardaespaldas más rápidos que no protegen al Bebé; remates de la Súper Monja (18 fotogramas) y del Párroco; variantes `arpg-exvotos` y `arpg-remates`. Escenarios PASS en emulador y jugado en la DS, sin log `perf`. **Falta:** `perf` con muchos poseídos, balance y dónde salen en el acto I. [`walkthrough`](../walkthroughs/arpg-exvoto-ramas/walkthrough.md).
- **Remate de la Súper Monja araña (`claude/remate-smonja-27d615`, 2026-11-23, sobre `claude/arpg-exvoto-ramas-a622a1`):** `L` sobre la Súper Monja tambaleante: el héroe le arranca la cabeza de un tirón amplio y el cuerpo araña cae espatarrado (variante B elegida por el usuario frente a un tirón más corto). Build `arpg-lab` 0 avisos; escenarios `remate_transicion_smonja` (oeste) y `_sur` PASS con GIF de la ROM. **Sin hacer:** `perf` en la DS y comprobar que el remate del Ojo sigue bien. [`walkthrough`](walkthroughs/remate-smonja/walkthrough.md).
