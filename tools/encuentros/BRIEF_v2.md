# Brief: encuentros v2 (catálogo aprobado por el usuario)

Mismo worktree `C:\codexlocal\dungeonds\.worktrees\encuentros-acto1`. No hagas commit. Reglas de `AGENTS.md`: sin `float`/`double`, sin warnings nuevos, efectos con colores apagados. La build por defecto no cambia: todo va bajo `ENCOUNTERS_PROTO`.

Diseño: `DESIGN.md` §6.13.6, párrafo «Tras la primera prueba en la DS (decidido 2026-11-17)». Catálogo: `walkthroughs/encuentros-acto1/catalogo-salas.html`. Datos: `tools/encuentros/acto1_v2.json`, generado por `tools/encuentros/catalogo_v2.py`; no lo edites a mano, edita el `.py`.

Tras la prueba en la DS, el usuario encontró el prototipo trivial. Hay que resolver ocho puntos:

1. **Datos v2.** `gen_act1_tables.py` lee `acto1_v2.json` (que `acto1.json` quede como histórico). El Cireneo pasa a 600 de vida. No hay `wave2`. Todos los enemigos van en estado `awake`.
2. **Todos presentes y despiertos a la vez.** Todos los enemigos de un encuentro aparecen con el bloque y **esperan quietos** en su sitio hasta que el héroe cruza el borde de abajo. Entonces despiertan todos a la vez, incluidos los Exvotos (sin el radio de 96 ni el «rezando»). Corrige el desvío actual: los `awake` echaban a andar al aparecer, con el héroe aún en el pasillo. Se mantiene la inmunidad mientras esperan.
3. **El Exvoto esquiva el rayo.**
   - Mientras el héroe carga el rayo, la línea de apuntado es la recta héroe→lápiz.
   - Los Exvotos despiertos a menos de ~14 px de esa línea, y por delante del héroe, se apartan perpendicularmente hacia **su** lado de la línea, según el signo del producto cruzado. Así una fila se abre cada uno a un lado.
   - Reacción de ~12 frames y paso lateral de ~20 frames. Después, enfriamiento de ~45 frames antes de volver a esquivar.
   - No esquivan si están a menos de ~24 px del héroe.
   - Además, al andar hacia el héroe no van en línea recta: cada uno lleva un sesgo lateral propio y estable, una ligera curva o zigzag lento.
   - Coste: un producto escalar y uno cruzado por Exvoto y frame, en punto fijo, solo mientras se carga. Nada de raíces en el bucle.
4. **El Cireneo, perseguidor que embiste** (como el demonio rosa de Doom).
   - Persigue siempre al héroe por el campo de navegación a una velocidad parecida a la del héroe andando.
   - Cuando lo tiene alineado (ángulo pequeño y distancia de 40 a 160 px, con línea de visión), telegrafía poco (~15 frames) y carga **muy rápido** en línea recta.
   - Si choca con una columna, estatua, saco, alambre, muro o banco, queda **aturdido ~90 frames**. Es la recompensa por usar el escenario.
   - Si la carga acaba sin chocar, recupera poco (~20 frames) y vuelve a perseguir.
   - Comprueba que el aturdimiento se da al chocar con banco, saco y alambre.
5. **Jefe con escolta.**
   - El Abanderado aparece con 2 Ojos y 1 Cireneo, además de sus Monaguillos.
   - Cuando muere un escolta, vuelve a entrar desde arriba (ly 8-24) a los ~4 s. Es el único sitio donde entran refuerzos.
   - Ajusta la vida del jefe para que con 12 Dones (el bot natural) dure 30-60 s.
6. **Alambre visible.** El placeholder del alambre es casi transparente y azulado y no se ve. Hazlo opaco: gris oscuro con púas más claras, igual de legible que los sacos y sin primarios.
7. **Colocación.**
   - Comprueba con la guía (punto 8) que ningún enemigo cae dentro de una pieza u obstáculo.
   - Comprueba que las piezas quedan donde dice el catálogo (±8 px).
   - Si algo no cuadra, corrige el `.py` y dime qué.
8. **Verificación.**
   - Compila `encuentros` y `encuentros-bot` con 0 warnings.
   - Regenera las capturas de la guía (`encuentros_guia.json`, sin las `_c`, porque ya no hay segunda oleada) en `artifacts/guia_v2/`, y mira las 18 `_a`.
   - Adapta el bot si hace falta: con esquivas y cargas nuevas, pon la reacción y el error de puntería del perfil torpe.
   - Corre `natural`, `natural_torpe` y `sin_mejoras_torpe`.
   - Entrega las tablas por encuentro (segundos y golpes), más golpes totales, vida mínima, duración y la duración del jefe.

Además, un GIF de 1 Exvoto esquivando el rayo y de 1 Cireneo embistiendo contra una estatua y quedando aturdido. Usa una escena montada con el héroe invulnerable, en frames a `artifacts/v2_gifs/<nombre>/`, uno cada 3-4 frames.

Entrega:
- archivos tocados;
- cifras;
- rutas de capturas y frames;
- todo lo que te hayas desviado del brief y por qué.
