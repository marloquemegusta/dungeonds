#ifndef ARPG_TREE_H
#define ARPG_TREE_H

// Skill tree (DESIGN.md 7.3). Node ids are bit indexes in g_arpg.tree; each node costs 1 point.
// Bought nodes are applied at the start of every dungeon run through the relics and Dones of upgrades.c.

#define ARPG_NODE_COUNT 13

int arpg_tree_has(int node);            // 1 if the node is bought
int arpg_tree_can_buy(int node);        // not owned, requirement owned, points > 0
int arpg_tree_buy(int node);            // spends a point, sets the bit, returns 1 on success
const char *arpg_tree_name(int node);
const char *arpg_tree_desc(int node);
int arpg_tree_branch(int node);         // 0 Metralleta, 1 Quemadura, 2 Veneno, 3 Resurreccion, -1 for node 0
void arpg_tree_apply(void);             // grants the effects of every owned node (call after upgrades_reset)

#endif
