#ifndef ARPG_INV_H
#define ARPG_INV_H

// Reliquias y tomos (DESIGN.md 7.4, opción B). Sustituye al árbol de habilidades:
// la bolsa son reliquias (engarces por escuela) y tomos (activan un hechizo). Todo estático.

#include <stdint.h>

#define ARPG_INV_BAG        16          // huecos de bolsa
#define ARPG_INV_SPELLS     3           // hechizos equipados: hueco 0 = Rayo, 1..2 = tomos
#define ARPG_INV_SCHOOLS    5           // Rayo, Ejecución, Glifo, Levantar, Pecho
#define ARPG_INV_SOCKETS    3           // engarces por escuela (Pecho usa 2)

// Escuelas (= pestañas del inventario).
enum {
    ARPG_SCHOOL_RAYO = 0,
    ARPG_SCHOOL_EJECUCION,
    ARPG_SCHOOL_GLIFO,
    ARPG_SCHOOL_LEVANTAR,
    ARPG_SCHOOL_PECHO
};

// Hechizos del menú radial.
enum { ARPG_SPELL_RAYO = 0, ARPG_SPELL_GLIFO = 1, ARPG_SPELL_LEVANTAR = 2 };

// Rarezas: [TUNABLE-PLACEHOLDER] cera que da desguazar.
enum { ARPG_RAR_COMMON = 0, ARPG_RAR_UNCOMMON, ARPG_RAR_RARE, ARPG_RAR_EPIC, ARPG_RAR_LEGENDARY, ARPG_RAR_COUNT };

// Tipos de objeto.
enum {
    ARPG_ITEM_EMPTY = 0,
    ARPG_ITEM_RELIC = 1,
    ARPG_ITEM_TOME = 2,
    ARPG_ITEM_RAYO = 3            // centinela del hueco 0 (Rayo, siempre equipado)
};

// Tipos de línea de estadística. Se aplican al equipar (ver arpg_inv_recalc).
enum {
    ARPG_LINE_DAMAGE = 0,         // Rayo: daño del rayo (Fervor). Ejecución: daño del remate/combo.
    ARPG_LINE_CHARGE,             // Rayo: carga más rápida (Prisa), en frames
    ARPG_LINE_RANGE,              // Rayo: alcance (Alcance), en px
    ARPG_LINE_BURN,               // Rayo: daño de fuego / quemadura (Brasa, Rescoldo), en %
    ARPG_LINE_LIFE,               // Pecho: vida máxima (Vida), en puntos
    ARPG_LINE_SPEED,              // Pecho: velocidad (Paso), en %
    ARPG_LINE_MANA,               // Pecho: maná máximo, en puntos
    ARPG_LINE_MANA_REGEN,         // Pecho: regeneración de maná, en %
    ARPG_LINE_REMATE_HEAL,        // Ejecución: +vida/maná al rematar, en puntos
    ARPG_LINE_COUNT
};

// Mecánicas (= ids de nodos antiguos, más las de Ejecución). Solo Rayo y Ejecución están definidos:
// Glifo y Levantar quedan sin mecánicas (sus pestañas muestran "Sin definir").
#define ARPG_MECH_NONE      0xFF
#define ARPG_MECH_GLIFO     0            // nodo 0: sólo con el tomo de Glifo equipado (sin contenido)
#define ARPG_MECH_PRISA     1
#define ARPG_MECH_SED_CENIZA 2
#define ARPG_MECH_LANZA     3
#define ARPG_MECH_LLAMA_VOTIVA 4
#define ARPG_MECH_BRASA     5
#define ARPG_MECH_AUTO_FE   6
#define ARPG_MECH_MIASMA    7            // Glifo: sin contenido
#define ARPG_MECH_CILICIO   8
#define ARPG_MECH_MARTIRIO  9
#define ARPG_MECH_LEVANTAR  10           // Levantar: sin contenido
#define ARPG_MECH_PROCESION 11           // Levantar: sin contenido
#define ARPG_MECH_OFRENDA   12           // Levantar: sin contenido
#define ARPG_MECH_VIATICO   13           // Ejecución: robo de vida al ejecutar (RELIC_VIATICO)
#define ARPG_MECH_FLAGELADO 14           // Ejecución: Corazón Flagelado (RELIC_FLAGELADO)
#define ARPG_MECH_PIRA      15           // Ejecución: Pira (al ejecutar quemado, explota y propaga)
#define ARPG_MECH_LLAGA     16           // Pecho: Llaga Abierta (más daño cuanta menos vida tienes)
#define ARPG_MECH_COUNT     17

typedef struct {
    uint8_t kind;                 // ARPG_ITEM_*
    uint8_t school;               // ARPG_SCHOOL_*
    uint8_t rarity;               // ARPG_RAR_*
    uint8_t mech;                 // id de mecánica (id de nodo antiguo) o ARPG_MECH_NONE
    uint8_t nlines;               // 0..2
    uint8_t line_kind[2];         // ARPG_LINE_*
    uint8_t mech_val;             // cifra propia del aura/mecánica (para comparar dos con la misma aura)
    int16_t line_val[2];          // valor entero (con signo)
    uint8_t level;                // nivel de objeto (1..99; 0 = 1)
    uint8_t name_id;              // 0 = genérico, >0 = nombre propio legendario
} ArpgInvItem;

typedef struct {
    ArpgInvItem bag[ARPG_INV_BAG];
    ArpgInvItem spell[ARPG_INV_SPELLS];                 // hueco 0 = Rayo (centinela)
    ArpgInvItem socket[ARPG_INV_SCHOOLS][ARPG_INV_SOCKETS];
    uint16_t wax;                                       // [TUNABLE-PLACEHOLDER]
} ArpgInventory;

// Resetea una estructura a vacío con el hueco 0 como Rayo.
void arpg_inv_init(ArpgInventory *inv);
// Partida nueva: bolsa con reliquias y tomos de ejemplo (fase 2).
void arpg_inv_new_game(void);
// Variante arpg-todo: equipa todos los tomos y reparte reliquias por escuela.
void arpg_inv_unlock_all(void);

int  arpg_inv_add(const ArpgInvItem *item);            // devuelve índice de bolsa o -1
int  arpg_inv_bag_count(void);
int  arpg_inv_bag_empty(int index);
const ArpgInvItem *arpg_inv_bag_item(int index);       // NULL si vacío/fuera
int  arpg_inv_first_free_bag(void);

int  arpg_inv_socket_count(int school);                // 3 (Pecho: 2)
const ArpgInvItem *arpg_inv_socket_item(int school, int socket);  // NULL si vacío

// Mueve un objeto de la bolsa a un engarce/ hueco de hechizo. 1 si pudo.
int  arpg_inv_equip_relic(int bag_index, int school, int socket);
int  arpg_inv_equip_tome(int bag_index);               // a un hueco de hechizo libre
int  arpg_inv_swap_relic(int bag_index, int school, int socket);   // intercambio
// Devuelve a la bolsa. 1 si pudo (había hueco).
int  arpg_inv_unequip_socket(int school, int socket);
int  arpg_inv_unequip_tome(int school);
// Desguaza un objeto de la bolsa por cera. 1 si lo hizo.
int  arpg_inv_scrap(int bag_index);
int  arpg_inv_wax_value(int rarity);

int  arpg_inv_has_spell(int spell);                    // 0 = Rayo siempre; 1/2 con tomo
// Id de hechizo (ARPG_SPELL_*) equipado en el hueco `slot` (0..2), o -1 si vacío.
int  arpg_inv_equipped_spell(int slot);
// Atributo por mecánica (id de nodo antiguo) equipada en cualquier engarce.
int  arpg_inv_has_mechanic(int mech);

// Modificadores: las líneas y mecánicas equipadas se aplican a g_mods (reutiliza los Dones y
// reliquias del roguelike). arpg_inv_apply() se llama al empezar la partida (tras mods_reset y
// upgrades_reset); arpg_inv_recalc() tras equipar/desequipar y aplica solo el delta.
void arpg_inv_apply(void);
void arpg_inv_recalc(void);

// Vista previa de engarce para la pantalla superior: totales de cada línea en los engarces de
// `school` antes y después de poner la reliquia de la bolsa en `socket` (intercambio incluido).
// Reutiliza el mismo reparto de líneas que compute_delta()/line_add(): la suma es por tipo de línea
// (Daño de Ejecución y de Rayo se muestran juntos porque la ficha es de una sola pestaña).
typedef struct {
    int valid;                          // 1 si la reliquia encaja en esa escuela/engarce
    int before[ARPG_LINE_COUNT];
    int after[ARPG_LINE_COUNT];
} ArpgInvPreview;

int arpg_inv_preview_socket(int bag_index, int school, int socket, ArpgInvPreview *out);

// Generación de reliquias (protodemo: Rayo, Ejecución, Pecho) escalada por nivel/piso.
void arpg_relic_roll(ArpgInvItem *out, int floor, int min_rarity, uint32_t *rng);
void arpg_relic_roll_school(ArpgInvItem *out, int school, int floor, int min_rarity, uint32_t *rng);

// Texto para la interfaz.
const char *arpg_inv_rarity_name(int rarity);
const char *arpg_inv_school_name(int school);
const char *arpg_inv_mechanic_name(int mech);
const char *arpg_inv_mechanic_desc(int mech);
void        arpg_inv_mechanic_format(const ArpgInvItem *it, char *buf, int n);
const char *arpg_inv_line_name(int kind);
const char *arpg_inv_item_name(const ArpgInvItem *it);

#endif // ARPG_INV_H
