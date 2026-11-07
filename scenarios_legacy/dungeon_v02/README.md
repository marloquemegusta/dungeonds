# scenarios_legacy/dungeon_v02

Escenarios de la mazmorra de la v0.2 (6 manadas dormidas, pedestales). Se movieron aquí el 2026-11-07 desde `scenarios/` porque la ROM principal arranca la franja desde la 0.3 mínima y pasaban en vacío, sin probar nada.

- `dungeon_pack_wakes_near_player.json`
- `dungeon_pack_reward_pedestals.json`

Están fuera de `scenarioDirectory`, así que ninguna suite los ejecuta. Para recuperarlos hace falta una variante de la ROM que arranque la mazmorra; hoy no existe en `.ds-game-dev/project.json` ni en `source/main.c` (el código de la v0.2 sigue en `main`, pero sin interruptor de arranque). Al crear esa variante, vuelve a apuntar `scenarioDirectory` o copia estos archivos a `scenarios/`.
