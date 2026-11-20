# Assets visuales pendientes (protodemo ARPG)

Diseño de referencia: `diseno_juego_final.md`. **P** = protodemo, **F** = juego final. **[ESTÉTICA]** = antes de generarlo hay que decidir el aspecto (ronda A/B/C con capturas de la ROM, como los efectos de armas). Lo marcado como procedural lo dibuja el código; solo hay que elegir su aspecto.

## 1. Mazmorra (Tripo + lab, kit de la catedral)
| # | Asset | Variantes | Prio |
|---|---|---|---|
| 1 | **Puerta lateral**: arco en el muro izquierdo y derecho | normal · cerrada con llave · atajo (cerrada por este lado) | P |
| 2 | **Puerta superior**: arco al fondo de la sala | normal · cerrada con llave | P |
| 3 | **Altar** (waypoint) | apagado · encendido | P |
| 4 | **Cofre** | cerrado · abierto; normal y de capilla (más rico) | P |
| 5 | **Objetos rompibles** de la nave | urna, cirio, exvoto de cera pequeño, con sus restos | P |
| 6 | **Lápida legible** (lore) | 1-2 modelos | P |
| 7 | **Prisionero** atado o encadenado | 1 | P si da tiempo |
| 8 | **Santuario** | 3 (uno por efecto) + versión gastada | F |
| 9 | Piezas de «catedral distorsionada» para variar las naves | 5-10 | F |

## 2. Personajes y enemigos
| # | Asset | Nota | Prio |
|---|---|---|---|
| 10 | **Exvotos por tamaño** (bebé, niño, adulta, grande, gigante) | En curso | P |
| 11 | **Siervo de cera** (nigromancia) | Puede ser un Exvoto con otro material o tinte | P si entra la nigromancia |
| 12 | **Mercader** del campamento | Personaje quieto con 1-2 animaciones | F (en P es un menú) |
| 13 | Abanderado élite | Por ahora, tinte | F |
| 14 | Familias de las zonas 2-5 y sus jefes | | F |

## 3. Animaciones del héroe (Mixamo + lab)
| # | Asset | Prio |
|---|---|---|
| 15 | **Puñetazo** (8 direcciones) | P |
| 16 | **Lanzar o dibujar un glifo** (8 direcciones) | P |
| 17 | **Levantar** (gesto de invocación) | P si entra la nigromancia |

## 4. Botín en el suelo (pequeños, 12×12; sustituyen a los placeholders de `tools/placeholders/`)
| # | Asset | Prio |
|---|---|---|
| 18 | **Reliquia** en el suelo | P (1 modelo, se tiñe por rareza) |
| 19 | **Runa** de experiencia | P |
| 20 | **Orbe de vida** y **orbe de maná** | P |
| 21 | **Cera** (la moneda) | P |
| 22 | **Llave** | P |
| 23 | **Poción** | P |

## 5. Efectos (procedurales en el suelo o en el cuerpo) [ESTÉTICA]
| # | Efecto | Prio |
|---|---|---|
| 24 | **Glifos**: dibujo de cada glifo en el suelo (lentitud, quemadura, juicio, marca) | P |
| 25 | **Aura de élite** (color por propiedad) y su nombre encima | P |
| 26 | **Botín que cae**: destello por rareza; columna de luz para la legendaria | P |
| 27 | Explosión de ejecución | P |
| 28 | Marca sobre un enemigo | P |
| 29 | Siervo que se levanta (la cera sube del suelo) | P si entra la nigromancia |

## 6. Interfaz [ESTÉTICA en casi todo]
| # | Pieza | Qué decidir | Prio |
|---|---|---|---|
| 30 | **Orbes de vida y maná** | Estilo (esfera de cristal renderizada, relicario con líquido, corazón y cáliz…), tamaño y si llevan número | P |
| 31 | **Hechizo activo** y cambio con `L` mantenido | Icono junto al orbe de maná; cómo se ve el cambio | P |
| 32 | **Pociones** | Dónde están y cómo se beben (propuesta: tocar el orbe con el lápiz) | P |
| 33 | **Barra de vida de élites y jefes** | En la pantalla superior, con nombre | P |
| 34 | **Nombre del botín en el suelo** | Tipografía y colores por rareza (blanco, verde, azul, morado, oro) | P |
| 35 | **Números de daño** | Fuente, tamaño, críticos | P |
| 36 | **Iconos de reliquias** | Uno por escuela + uno para pasivas, teñidos por rareza (16×16 o 24×24) | P |
| 37 | **Iconos de hechizos** | Rayo, Ejecución, Glifo, Levantar | P |
| 38 | **Pantalla de bolsa y huecos** | Marco, casillas, cómo se ven los huecos de cada hechizo | P |
| 39 | **Carta de reliquia y comparación** | Lo que llevas frente a lo nuevo; líneas que suben y bajan | P |
| 40 | **Mapa** de la zona | Estilo: plano a tinta, pergamino, vidriera… | P |
| 41 | **Campamento** | Ilustración o render de fondo (hoguera, cama, sitio para el mercader) | P |
| 42 | Dormir / subir de nivel | Fogonazo y texto | P |
| 43 | Iconos de mapa | Altar, puerta con llave, cofre, secreto | P |

## 7. Sonido (no visual; para tenerlo en la lista)
Puñetazo, glifo, levantar, recoger runa, orbe, reliquia por rareza, desguazar, abrir puerta, cofre, altar, dormir. F salvo los de botín.

## Orden recomendado
1. Lo que bloquea el código de la mazmorra: **1, 2, 3, 4** (puertas, altar, cofre).
2. Botín en el suelo: **18-23** (pequeño y rápido).
3. Rondas de estética de la interfaz: **30, 34, 36, 38-39, 40**.
4. Animaciones **15-16** y efectos **24-26**.
