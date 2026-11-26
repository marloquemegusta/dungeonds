# ARPG: luz por sala cargada en la ROM

Cada sala de la zona 1 carga en la pantalla de carga el paquete `nitrofiles/arpg_luz/<luz>.bin` de su ambiente (kit de catedral, héroe, tablas de enemigos; clips y remates se leen del mismo fichero). Si falta el paquete se queda el arte de día.

Evidencia: `assets/rom_luces.png` (una captura de la ROM por luz, 12 luces; escenario `scenarios/arpg_luz_sala.json`, PASS). Detalle técnico en `TECHNICAL.md` 5.7.

MDs revisados: solo `TECHNICAL.md` 5.7 (cargador). Sin sincronizar con `main` (WIP).
