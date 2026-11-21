#ifndef ARPG_TREE_H
#define ARPG_TREE_H

// Shim del antiguo árbol de habilidades (DESIGN.md 7.3), que desaparece en favor de las
// reliquias y tomos del inventario (arpg_inv.h). Los ids de nodo son los mismos y el
// API se mantiene para no tocar los módulos que ya lo leían (curse, allies, gameplay, main,
// radial): arpg_tree_has(n) devuelve 1 si hay una reliquia equipada cuya mecánica es ese
// nodo, o el tomo del Glifo para el nodo 0.

#define ARPG_NODE_COUNT 13

int arpg_tree_has(int node);            // 1 si la mecánica (reliquia/tomo equipado) está activa
void arpg_tree_apply(void);             // aplica los efectos de cada mecánica equipada (tras upgrades_reset)

#endif
