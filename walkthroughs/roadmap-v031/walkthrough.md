# Hoja de ruta por versiones: 0.3.1 → 0.6 (2026-11-07)

Rama `docs/roadmap-v031`. Solo documentación, sin código.

## Qué se decidió
- **La 0.3 mínima se da por cerrada:** fusionada en `main`, sin warnings, con tests y escenarios en verde y 60 FPS medidos en la DS. El usuario dice que "se siente como un juego real".
- El plan de `DESIGN.md` §6.9, que iba por pasos técnicos, se sustituye por **versiones jugables**, cada una con su sesión y su rama:

| Versión | Contenido |
| :--- | :--- |
| 0.3.1 | Tuning y pulido sin mecánicas nuevas (§6.9.1). |
| 0.4 | Gemas, nivel, 1 de 3 mejoras, clases y controles de §6.5 (§6.9.2). |
| 0.5 | Enjambre, élites, cofres, emboscadas y pool de 48 (§6.9.3). |
| 0.6 | Tramos a mano, dos biomas, minijefe y jefe: la prueba completa (§6.9.4). |

- La sesión de diseño de contenido deja de ser un único paso al principio: cada versión empieza por la parte que necesita (regla 9). Las secciones de la 0.4 a la 0.6 están marcadas como borrador y se revisarán con el feedback de cada versión.
- **Ancho de la franja: 512 px.** El usuario prefiere el de la 0.3 mínima a los 256–384 px que proponía §6.2, que se actualiza.

## Documentos tocados
- `DESIGN.md`: §3 (decisiones por versión), §6.0 marcada como cerrada, §6.2 con el ancho de 512 px, y §6.9 reescrita con la tabla y las subsecciones 6.9.1–6.9.4.
- `TECHNICAL.md` §4.7:
  - lo que implementó la 0.3 mínima: ventana con rebase, navegación de 48×128, horda, marea por hardware y medición en la DS;
  - las notas de la v0.2 marcadas como tales.
- `STATUS.md`: estado actual, siguientes pasos por versión y esta entrega.
- `AGENTS.md`:
  - delegación en modelos de otros proveedores con `delegate-agents`;
  - límite del sandbox de los agentes Codex.
