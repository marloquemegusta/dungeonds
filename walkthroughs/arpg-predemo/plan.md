# Plan: pre-demo ARPG (rama `proto/arpg`)

Diseño: `DESIGN.md` §7. Worktree: `C:\codexlocal\dungeonds\.worktrees\arpg`. Todas las fases las implementa un subagente **Haiku** (petición expresa del usuario), una tras otra porque casi todas tocan `source/main.c`. El coordinador compila, mira capturas y corrige el rumbo entre fases.

## Reglas para cada fase
- Solo la ROM por defecto importa (variant `default`, que ya activa `ENCOUNTERS_PROTO=1`). Las variantes de pruebas pueden quedarse como están si no compilan con el cambio solo cuando su código esté protegido por `#if`; la default tiene que compilar con **0 avisos**.
- Sin `float` ni `double` (NDS sin FPU). Enteros y punto fijo (`fixed` 8.8 de `game.h`).
- Colores apagados (paleta `FX_SH_*` de `source/weapons.c`, `DESIGN.md` §6.10): nada de primarios puros.
- Cifras nuevas como `#define` con el comentario `// [TUNABLE-PLACEHOLDER]`, agrupadas en `include/arpg.h` (se crea en la fase 1).
- Compilar: `powershell -NonInteractive -ExecutionPolicy Bypass -File C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1 -ProjectPath C:\codexlocal\dungeonds\.worktrees\arpg` (debe acabar en `DS_BUILD=PASS ... new_warnings=0`).
- No ejecutar tests ni escenarios. No hacer commits.

## Cifras preliminares (todas `[TUNABLE-PLACEHOLDER]`)
| Qué | Valor |
|---|---|
| Vida del héroe | 100 base, +10 por nivel |
| Maná | 60 base, +5 por nivel; regenera 1 punto cada 30 frames |
| Daño recibido por golpe | Exvoto 15, Monaguillo 10, Cireneo 25, Ojo 30, Abanderado 25, otros 20 |
| Rayo | cuesta 15 de maná por disparo; daño base 100 (antes 150) |
| Puñetazo (`L` sin nadie tambaleante) | 50 de daño, alcance 28 px de suelo, recarga 24 frames; si no mata, deja tambaleante |
| Remate | 60 % suelta orbe de vida (+20), 75 % suelta orbe de maná (+25) |
| Experiencia por muerte | Exvoto 4, Monaguillo 1, Cireneo 10, Ojo 8, Abanderado 100 / 200 / 400 (stages 5 / 10 / 15) |
| Experiencia para pasar del nivel L al L+1 | 25 × 1,45^(L−1), en tabla entera hasta nivel 20 |
| Vida enemiga por profundidad | × (100 + 12 × stage) / 100, stage 0..14 |
| Jefe 2 (stage 10) | vida × 1,6 extra, hasta 12 monaguillos |
| Jefe 3 (stage 15) | vida × 2,2 extra, escolta de 2 Ojos y 2 Cireneos |
| Maldición | 30 de maná; radio 40 px; dura 240 frames; 1 capa de Quemado cada 30 frames a quien esté dentro; lanzamiento hasta 140 px |
| Veneno 1 | radio 56, duración × 1,5 |
| Resurrección | R1: máx. 2 aliados, 300 frames; R2: máx. 4, 480 frames; R3: explotan al morir (120 de daño de fuego, radio 40) |

## Fases
1. **Vida y maná con orbes.** Vida en puntos y maná en `PlayerState`; daño por tipo de enemigo; regeneración de maná; dos orbes en el HUD de la pantalla inferior en lugar de los corazones.
2. **Coste del rayo, puñetazo y botín del remate.** El rayo no se puede cargar sin maná y lo gasta al disparar; `L` corto hace puñetazo si no hay remate; el remate suelta orbes de vida y maná (sistema `pickups`).
3. **Experiencia sin cartas.** Experiencia por muerte, tabla de niveles, sin relicarios ni relicario dorado ni pantalla de cartas en la mazmorra; la experiencia no se pierde al reiniciar.
4. **Campamento, dormir y guardado.** Menú del campamento (Dormir, Entrar en la Catedral, Códice), pausa con «Volver al campamento», morir lleva al campamento, guardado en la tarjeta, título con Continuar / Nueva partida.
5. **Árbol.** Pantalla del árbol al dormir; nodos aplicados con las reliquias y Dones existentes.
6. **Maldición y cambio de hechizo.** Granada rescatada como Maldición; `L` mantenido cambia de hechizo; rama Veneno.
7. **Resurrección.** Exvotos aliados.
8. **Mazmorra infinita y jefes élite.** Sin pasillos (sala tras sala), sin Altar, piso infinito con jefe cada 5 y escalado por piso. Sin atajos.
9. **Placeholders y lista de assets.** Paralelepípedos de color en Blender renderizados con el lab para lo que no tenga gráfico (runa de experiencia, orbes de vida y maná del suelo, proyectil y zona de la maldición, marca de aliado…); lista de assets que el usuario debe pre-renderizar.

**Decisiones de 2026-11-19 (segunda tanda):** sin relicarios de ningún tipo; la experiencia cae como runas que se recogen y los jefes sueltan más; sin mercader; sin pasillos; mazmorra infinita; sin atajos.
