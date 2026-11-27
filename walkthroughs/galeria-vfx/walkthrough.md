# Galería de efectos del roguelike

15 GIFs de los efectos finales del roguelike, uno por efecto con la variante elegida en las rondas A/B/C, capturados de la ROM `cathedral-sandbox`. Vista completa en [`galeria.html`](galeria.html) y en el Artifact https://claude.ai/artifact/ASFM2r7Tb4zwgMN83tRnqq.

| Efecto | Reliquia | Variante | Qué se ve |
| :--- | :--- | :--- | :--- |
| [enemigo_quemado_A](assets/01_enemigo_quemado_A.gif) | (estado quemado) | A | Brasas y lenguas sobre tres enemigos con 1, 2 y 4 capas de quemadura. |
| [enemigo_quemado_B](assets/02_enemigo_quemado_B.gif) | (estado quemado) | B | Corona de llamas a los pies de tres enemigos con 1, 2 y 4 capas. |
| [auto_de_fe_A](assets/03_auto_de_fe_A.gif) | Auto de Fe | A | Carga, disparo sobre enemigo quemado y chispas al impactar. |
| [auto_de_fe_C](assets/04_auto_de_fe_C.gif) | Auto de Fe | C | Corona de llamas a los pies; el disparo la consume y sube evaporandose. |
| [llama_votiva_B](assets/05_llama_votiva_B.gif) | Llama Votiva | B | Chispas que giran irregulares en la linea de apuntado durante la carga. |
| [corazon_flagelado_A](assets/06_corazon_flagelado_A.gif) | Corazon Flagelado | A | Onda en anillo grande alrededor del heroe que alcanza a los enemigos. |
| [martirio_contagioso_A](assets/07_martirio_contagioso_A.gif) | Martirio Contagioso | A | Disparo a un enemigo quemado: estalla y el anillo contagia a los vecinos. |
| [llaga_abierta_B](assets/08_llaga_abierta_B.gif) | Llaga Abierta | B | Heroe te�ido de dorado palido con sangre que gotea, a 4, 3, 2 y 1 corazones. |
| [viatico_A](assets/09_viatico_A.gif) | Viatico | A | Hilo de sangre que sale del enemigo muerto y fluye al pecho del heroe. |
| [viatico_C](assets/10_viatico_C.gif) | Viatico | C | Alma palida que sale del enemigo muerto y entra en el heroe. |
| [aura_E_cilicio](assets/11_aura_E_cilicio.gif) | Aura de Cilicio | - | Corona de espinas en el suelo durante la carga; el aro quema al enemigo; disparo. |
| [aura_H_ceniza](assets/12_aura_H_ceniza.gif) | Sed de Ceniza | - | Ceniza alrededor del heroe durante la carga y disparo. |
| [aura_G_gloria](assets/13_aura_G_gloria.gif) | Viatico | - | Gloria (halo) durante la carga y disparo. |
| [aura_L_llamas](assets/14_aura_L_llamas.gif) | Corazon Flagelado | - | Llamas alrededor del heroe durante la carga y disparo. |
| [rayo_base](assets/15_rayo_base.gif) | (ninguna) | - | Carga y disparo del rayo base (haz fuego) sin reliquias. |

## Regenerar

`tools/galeria_vfx.py` genera los escenarios `scenarios/galeria_*.json`; compilar con `-Variant cathedral-sandbox`, ejecutar los escenarios y `tools/galeria_gifs.py` compone GIFs y contactos. La cámara real tiene los pies del héroe en y≈95 de la pantalla inferior y la carga mínima es >26 frames; por eso el antiguo `abc_scenes.py` fallaba.

## Avisos

- El aura L (llamas) se fuerza con `g_aura_debug_mask`.
- La ceniza (aura H) es casi inapreciable.

MDs: solo se añade la nota del catálogo en `DESIGN-ARPG.md` §5.
