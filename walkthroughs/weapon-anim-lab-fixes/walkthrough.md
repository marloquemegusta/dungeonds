# Correcciones de animación, retargeting e IK de armas

## Alcance

Trabajo en `fix/weapon-anim-diagnosis`, dentro del worktree `.worktrees/weapon-anim-diagnosis`; `main` permanece intacta. Se corrigió el motor compartido de extracción, retargeting, poses por capas, alineación de armas, soporte IK y horneado FBX. El extractor admite además los proxies Mesh animados de `skeleton_death.fbx` únicamente cuando el modelo no contiene ningún Bone humanoide mapeado y el clip tiene tracks de posición o cuaternión para esos nodos.

## Verificación de motor

- La discontinuidad máxima de cabeza en `rifle_idle` bajó de **0.9439588** a **0.0001027575** alturas de personaje a lo largo de 186 muestras.
- En AK-47, carabina, escopeta y rifle de francotirador, yaw semántico de 90° produce 90° de giro de cañón; roll de 90° gira 90° el eje físico superior sin mover el pivote de agarre; el avance semántico queda alineado con el cañón.
- **60 casos de contacto de palma** (5 personajes × 4 armas × 3 fases de apuntado) son alcanzables; error máximo **4.59677e-8** alturas de personaje.
- En cuatro fases híbridas, la mezcla conserva las rotaciones locales de parte superior e inferior con error máximo **4.22e-8 rad**; el error de cadera es cero.
- El catálogo conserva 11 clips compartidos únicos (9 fuentes base y 2 híbridos), incluido el clip de muerte con proxies Mesh; un FBX de personaje puede aportar clips propios al visor. Pasan las suites de motor, catálogo, splicer, E2E y regresión de laboratorio, además del chequeo de sintaxis. La verificación E2E exportó un FBX de 22.72 MB y lo cargó en el visor renderer.

## Criterio de deduplicación

Se elimina una fila solo si el mismo movimiento tiene duración, número de muestras, conjunto de pistas canónicas y todos sus valores muestreados idénticos. Con este criterio, `Slash.fbx` y `JumpHit.fbx` son duplicados: ambos producen 59 muestras y las mismas 23 pistas con valores exactos. Se conserva `melee_slash`; `melee_jump_hit` deja de ser una fila del catálogo. La regresión compara ambas fuentes y obliga a reconsiderar la deduplicación si `JumpHit.fbx` cambia. Nombre o parecido de pose no bastan: caminar, correr, agacharse y sus dos híbridos de apuntado siguen siendo clips separados.

## Integración y límites

El catálogo (2.33 MB) y el HTML autónomo (3.28 MB) incluyen `rifle_walk_ready` («Caminar en ristre») y `rifle_run_ready` («Correr en ristre»), mezclando locomoción inferior y apuntado superior. La matriz headless cubrió 5 personajes y 4 armas: cargó 14 mapas FBM de shotgun (4,424,669 bytes, 14 grupos) y 13 de sniper (6,641,310 bytes, 13 grupos); probó ambos modos con ambas armas, sin errores JavaScript. También verificó que `Death Fall` aparece en Combat, se selecciona y queda preparado para retarget (1.233 s). El contacto máximo fue **1.61e-8** alturas y el producto punto de orientación ≈1. Shotgun y sniper exportaron y reimportaron ambos híbridos (`rifle_walk_ready` y `rifle_run_ready`). Shotgun conserva 14 materiales y mapas del arma; sniper conserva sus 13 slots, grupos y mapas. Cada FBX reimportado incluye 19 nodos Texture y 19 Video y 15 Material para shotgun, o 18 Texture y 18 Video y 14 Material para sniper; esos conteos incluyen los materiales del personaje. Se guardaron 10 capturas y `headless-summary.json` en `assets/`. No se afirma rendimiento ni validación en Nintendo DS: este trabajo corresponde al laboratorio web.
