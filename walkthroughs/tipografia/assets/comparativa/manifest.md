# Comparativa ANTES / DESPUES de la tipografia

ANTES = commit d65c39d (Georgia + 5x7) con solo el arreglo SKIP_TITLE. DESPUES = rama feat/tipografia sin commitear. PNG de 256x192 (pantalla inferior de la captura de 256x384), sin ampliar. Las capturas salen de escenarios temporales (`cmp_menus`, `cmp_jefe_*`) escritos en el scratchpad, mas `intro_tarjetas` del repo. Las ofertas de dones son aleatorias.

| Par | Pantalla | Origen | Observaciones |
| :--- | :--- | :--- | :--- |
| 01_titulo | Menu de titulo (Nueva partida / Codice / Controles) | cmp_menus, `00_titulo` (150 frames) | DESPUES con Palatino en botones. La pantalla superior no muestra logo en ninguna de las dos versiones. |
| 02_pausa | Pausa en partida (4 botones) | cmp_menus, `05_pausa` (START para saltar intro, START para pausar) | Se ven los 4 botones y el HUD. Texto cabe en ambas. |
| 03_controles | Controles | cmp_menus, `01_controles` | Todo cabe. ANTES sin parentesis ("PRUEBA"), DESPUES con "(prueba)". |
| 04_codice_corazon_abierto | Ficha 1/5 | cmp_menus, `02_codice_1` | Sin fila de datos. Sin cortes en ninguna. |
| 05_codice_exvoto | Ficha 2/5 | cmp_menus, `02_codice_2` | Fila VIDA/VELOC./AMENAZA cabe en el marco en DESPUES (termina antes del borde derecho); la fila queda en gris claro, mas tenue que el resto del texto. |
| 06_codice_abanderado | Ficha 5/5 | cmp_menus, `02_codice_5` | Igual: la fila cabe en DESPUES. El texto de lore ocupa hasta la linea "Mientras el asta..." sin tocar los botones. |
| 07_intro_catedral | Tarjeta 1/4 | intro_tarjetas, `01_catedral_b` | Sin cortes. |
| 08_intro_apuntar | Tarjeta 2/4 | intro_tarjetas, `02_apuntar_b` | Sin cortes. |
| 09_intro_marea | Tarjeta 3/4 | intro_tarjetas, `03_marea_b` | Sin cortes. |
| 10_intro_vida | Tarjeta 4/4 | intro_tarjetas, `04_corazon_b` | Sin cortes; el reflujo de linea cambia ("a / veces"). |
| 11_hud_partida | HUD en partida (Enc. 1 de 14, Altura, Tiempo) | cmp_menus, `04_partida` | DESPUES "Altura 0 m". Sin solapes. "Manadas" y el nombre de pedestal NO existen en esta ROM (solo en la rama no-encuentros del HUD), por eso no hay pares de pedestal. |
| 12_dones_nivel | Pantalla de subida de nivel con 3 cartas (Vida I seleccionada) | cmp_jefe_*, `c_dones_1` (ANTES) / `b_dones_0` (DESPUES); se fuerza con `g_upg_debug` (`apply_seq`=1, `force_levelups`=1 en offset 17) | Las cartas ofrecidas difieren (azar) pero el texto del efecto es el mismo. En DESPUES "Jefe 5 de 14" (arriba izq.) queda tapado en parte por la carta seleccionada; la "A" de la esquina superior derecha sale cortada por el borde (tambien en ANTES). |
| 13_reliquia | Pantalla de Reliquia (Viatico seleccionado) | cmp_jefe_*, `victoria_0092` (tras matar al jefe) | La reja de la sala del jefe se dibuja encima de las cartas y tapa los nombres de las otras dos (ANTES y DESPUES por igual): no permite juzgar si "Paso de procesion" / "Lanza de Longino" caben en dos lineas. Texto del efecto abajo correcto. |
| 14_jefe_intro | Intro del jefe: nombre, capitan y cita | cmp_jefe_*, `intro_0084` | Texto completo (cita ya tecleada). Sin cortes. DESPUES con tipo mas fino y claro. |
| 15_jefe_victoria | Victoria sobre el jefe: nombre tachado y "El asta ha caido." | cmp_jefe_*, `victoria_0082` | Sin cortes. |
| 16_jefe_hud_combate | HUD del jefe en combate (barra EL ABANDERADO + corazones) | cmp_jefe_*, `f_combate` | La reja tapa parte de "Altura/Tiempo" abajo a la izquierda (ambas). |

Notas generales: los textos de la pantalla superior de las tarjetas de introduccion (HUD dentro del video, "ALTURA 1M") siguen en la fuente antigua en DESPUES porque van horneados en el video.
