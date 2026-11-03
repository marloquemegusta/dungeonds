# Diseño de gameplay mínimo (2026-11-03)

Sesión de diseño en formato entrevista. Sin cambios de código; la fuente de verdad es `DESIGN.md` §1 y §4.

## Punto de partida
`DESIGN.md` §4 describía un juego completo (4 armas con munición, vida + armadura, pickups, detección por ruido, generador). Demasiado para saber si el combate es divertido.

## Referentes del usuario
- **Doom:** feel de las armas (la escopeta), strafe, arenas con muchos enemigos, esquivar ataques.
- **Hotline Miami:** control preciso, frenetismo, salas como puzzle de prioridades.
- **Diablo / Vampire Survivors:** loot y progresión. Aparcados hasta validar el combate.

## Decisiones
| Tema | Decisión |
| :--- | :--- |
| Controles | D-pad mueve, stylus apunta por dirección, L cambia de arma. Solo L es usable sin dejar de apuntar. |
| Salud | 4–5 golpes, i-frames, reinicio instantáneo de la arena, vida llena por arena. |
| Escopeta | Un disparo por toque, bombeo, empujón al enemigo. |
| Francotirador | Al tocar se para y apunta; dispara al levantar; apuntado mínimo ~0,4 s; atraviesa; cancelable. |
| Munición | Infinita; el coste es el ritmo y quedarse quieto al apuntar. |
| Cargador | Estilo Pinky (persecución sin telegraph). Necesita navegación BFS: hoy es lento y no encuentra al jugador. |
| Tirador | Banda de distancia, strafe, destello ~0,3 s antes de ráfaga de 3. |
| Salas | Arena cerrada, todos se activan al entrar; 3–4 mapas nuevos hechos a mano. |
| Feel | Hitstop, destello blanco, temblor de pantalla, retroceso, empujón, fragmentos; destello rojo al recibir daño. |
| Fuera | Enemigo grande, loot, mejoras, generador procedural. |

## Abierto
Forma de los mapas de arena y sonido (`DESIGN.md` §3); números de tuning (§4.7).
