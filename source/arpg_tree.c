#include "arpg_tree.h"
#include "arpg_inv.h"
#include "upgrades.h"

// El árbol ya no existe: cada id de nodo es ahora una mecánica de reliquia. El nodo 0
// (Glifo) se tiene con el tomo equipado; el resto, con una reliquia engarzada cuya
// mecánica sea ese id. Así el resto del código sigue leyendo arpg_tree_has(n) igual.

int arpg_tree_has(int node) {
    if ((unsigned)node >= ARPG_NODE_COUNT) return 0;
    if (node == 0) return arpg_inv_has_spell(ARPG_SPELL_GLIFO);
    return arpg_inv_has_mechanic(node);
}

// Efectos que actúan al empezar la partida y que no cubre el inventario: las mecánicas sin
// reliquia propia que en el árbol eran Dones (Prisa y Brasa). Las reliquias con bit propio
// (Sed de Ceniza, Lanza, Llama Votiva, Auto de Fe, Cilicio, Martirio, Procesión, Viático,
// Flagelado) las concede arpg_inv_apply(); aquí no se tocan para no duplicar.
void arpg_tree_apply(void) {
    if (arpg_tree_has(1)) upgrades_set_don_rank(DON_PRISA, 4);   // Prisa (nodo 1)
    if (arpg_tree_has(5)) {                                       // Brasa (nodo 5)
        upgrades_set_don_rank(DON_BRASA, 4);
        upgrades_set_don_rank(DON_RESCOLDO, 2);
    }
}
