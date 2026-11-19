# Ojo táctico, guarnición y Ojo en todas las salas (rama `feat/ojo-alcance`, 2026-11-19)

Primera vuelta del método «sala a sala» (`DESIGN.md` §6.13.10): se jugó la ROM de `main` como línea base y se fue iterando sobre la ROM normal con el usuario, en cinco subidas a la DS. Registro de pruebas en `walkthroughs/sala-atrio/plan_pruebas.md`.

## Qué cambió en la ROM
- **El Ojo no tiene alcance:** solo le corta la vista una columna o una estatua. Se mantienen como máximo dos Ojos apuntando a la vez.
- **Un Ojo en todas las salas del acto I**, también en las ligeras y medias que no lo tenían (procesión, pinza, claro, alambrada): 7 Ojos nuevos en `tools/encuentros/acto1_v2.json`.
- **Guarnición arriba:** estado nuevo `ENEMY_STATE_GUARD` para Exvotos y Cireneos que despiertan con la sala pero se quedan junto a su Ojo. Se sueltan si el héroe se acerca a 220 de suelo, si reciben daño o si muere el Ojo al que guardan. Ligera: +2 Exvotos por sala; media y dura: +2/+3 Exvotos y un Cireneo de guardia (hasta 19 enemigos en la peor sala, tope 24).
- **Ojo tirador táctico** (solo en salas de encuentros; en la horda conserva su comportamiento antiguo):
  - Héroe agachado tras banco o saco: el Ojo se queda quieto, sin disparar, mirándole. Al quedar expuesto arranca el ciclo normal completo (apuntar 40 + fijar 20 frames) y el héroe tiene el mismo margen para esquivar que ante cualquier apuntado.
  - Columnas y estatuas: el Ojo sigue al héroe todo el rato. Cada 8 frames comprueba la línea al héroe ahora y a 30 frames vista y, si falta alguna, anda al punto más cercano que las tenga. Correa de 288 de suelo y 80 px de bajada, que crece 96 por segundo sin línea hasta cubrir toda la sala.
  - No se frena con su propia guardia, no se mueve mientras apunta y, sin hueco de apuntado, se queda quieto.

## Qué averiguamos en el camino
- El alcance se mide en suelo isométrico (cada px vertical cuenta doble): «320 px» solo cubría la mitad de arriba de la sala; para cubrirla entera hacían falta ~640. Por eso se pasó a «sin alcance».
- El Ojo no se recolocaba porque, con cobertura baja, veía al héroe (el banco no corta la línea de visión) y disparaba contra el banco para siempre, sin que le saltara nunca la regla de recolocación.
- Una recolocación tímida (2 s de espera, mitad de velocidad) se percibía como «no se mueve»; los tiempos medidos están en el registro de pruebas.

## Qué no cambia / queda pendiente
- **Flanqueo coordinado de los Exvotos** (reunirse fuera de alcance, entrar juntos, rodear la cobertura): sin programar.
- **Catálogo v3 de salas** (atrio, trinchera, etc.): solo diseño; la ROM sigue con las plantas v2. `catalogo_v2.py` está obsoleto (reescribe el JSON con datos viejos): no ejecutarlo.
- **El Ojo anda a un tercio de la velocidad del héroe:** mantiene la línea solo ~57 % del tiempo con el héroe andando por delante de una columna. Palancas sin decidir: velocidad de persecución mayor y menos tiempo parado al apuntar.
- **El ciclo completo al salir de cobertura** (última versión) **no se jugó en la DS**; sí se midió en escena (60 frames hasta el disparo, igual que el ciclo normal). La versión anterior, con 12 frames de aviso, «pillaba siempre».
- **Rendimiento sin medir con `perf`** en la DS (rayo largo y búsqueda de posición cada 8 frames por Ojo). El usuario no notó tirones jugando. Pendiente antes de dar la mecánica por cerrada (`AGENTS.md` regla 6).
- Constantes `[TUNABLE-PLACEHOLDER]` en `include/gameplay.h` (`OJO_*`, `GUARD_*`).
