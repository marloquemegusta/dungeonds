#include "arpg_tree.h"
#include "arpg_progress.h"
#include "upgrades.h"

typedef struct {
    const char *name;
    const char *desc;
    int branch;     // 0 Metralleta, 1 Quemadura, 2 Veneno, 3 Resurreccion, -1 for node 0
    int requires;   // node id that must be owned first, -1 for none
} TreeNode;

static const TreeNode s_nodes[ARPG_NODE_COUNT] = {
    { "Maldici\xC3\xB3n",     "Desbloquea la Maldici\xC3\xB3n (L mantenido)", -1, -1 },
    { "Prisa",                "Carga del rayo m\xC3\xA1s r\xC3\xA1pida",        0, -1 },
    { "Sed de Ceniza",        "Cada muerte acelera la siguiente carga",       0, 1 },
    { "Lanza",                "El rayo atraviesa a todos",                    0, 2 },
    { "Llama Votiva",         "La l\xC3\xADnea de apuntado quema",             1, -1 },
    { "Brasa",                "M\xC3\xA1s da\xC3\xB1o de fuego y quemaduras largas", 1, 4 },
    { "Auto de Fe",           "Doble da\xC3\xB1o a los quemados",             1, 5 },
    { "Miasma",               "Zona de maldici\xC3\xB3n m\xC3\xA1s grande y larga", 2, 0 },
    { "Cilicio",              "Aro de brasas a tus pies al cargar",           2, 7 },
    { "Martirio",             "Los quemados explotan al morir",               2, 8 },
    { "Levantar",             "Los muertos en tu maldici\xC3\xB3n luchan por ti", 3, 0 },
    { "Procesi\xC3\xB3n",     "M\xC3\xA1s aliados y duran m\xC3\xA1s",         3, 10 },
    { "Ofrenda",              "Los aliados explotan al caer",                 3, 11 },
};

int arpg_tree_has(int node) {
    return (unsigned)node < ARPG_NODE_COUNT && ((g_arpg.tree >> node) & 1u) != 0;
}

int arpg_tree_can_buy(int node) {
    if ((unsigned)node >= ARPG_NODE_COUNT) return 0;
    if (arpg_tree_has(node)) return 0;
    if (s_nodes[node].requires >= 0 && !arpg_tree_has(s_nodes[node].requires)) return 0;
    return g_arpg.points > 0;
}

int arpg_tree_buy(int node) {
    if (!arpg_tree_can_buy(node)) return 0;
    g_arpg.points--;
    g_arpg.tree |= (uint16_t)(1u << node);
    return 1;
}

const char *arpg_tree_name(int node) {
    return (unsigned)node < ARPG_NODE_COUNT ? s_nodes[node].name : "";
}

const char *arpg_tree_desc(int node) {
    return (unsigned)node < ARPG_NODE_COUNT ? s_nodes[node].desc : "";
}

int arpg_tree_branch(int node) {
    return (unsigned)node < ARPG_NODE_COUNT ? s_nodes[node].branch : -1;
}

// Effects of the nodes that act now. Nodes 0, 7, 10, 11 and 12 only set their bit (later phases read it).
void arpg_tree_apply(void) {
    for (int n = 0; n < ARPG_NODE_COUNT; n++) {
        if (!arpg_tree_has(n)) continue;
        switch (n) {
        case 1:  upgrades_set_don_rank(DON_PRISA, 4); break;
        case 2:  upgrades_grant_relic(RELIC_SED_CENIZA); break;
        case 3:  upgrades_grant_relic(RELIC_LANZA); break;
        case 4:  upgrades_grant_relic(RELIC_LLAMA_VOTIVA); break;
        case 5:
            upgrades_set_don_rank(DON_BRASA, 4);
            upgrades_set_don_rank(DON_RESCOLDO, 2);
            break;
        case 6:  upgrades_grant_relic(RELIC_AUTO_FE); break;
        case 8:  upgrades_grant_relic(RELIC_CILICIO); break;
        case 9:  upgrades_grant_relic(RELIC_MARTIRIO); break;
        default: break;
        }
    }
}
