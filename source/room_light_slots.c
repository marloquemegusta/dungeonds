// Generado por tools/room_light_slots.py: destinos de los sprites del heroe y tablas de enemigos que sustituye el
// paquete de luz de cada sala (orden del paquete = orden de los arrays de source/player_sprite.c).
#include "room_light.h"

extern uint8_t g_player_frames[];
extern uint8_t g_player_frame_offsets[];
extern uint8_t g_player_frame_bounds[];
extern uint8_t g_player_runs[];
extern uint8_t g_player_run_offsets[];
extern uint8_t g_player_shadow_masks[];
extern uint8_t g_player_shadow_offsets[];
extern uint8_t g_player_shadow_bounds[];
extern uint8_t g_charger_frame_offsets[];
extern uint8_t g_charger_frame_bounds[];
extern uint8_t g_charger_run_offsets[];
extern uint8_t g_charger_shadow_offsets[];
extern uint8_t g_charger_shadow_bounds[];
extern uint8_t g_ojo_frame_offsets[];
extern uint8_t g_ojo_frame_bounds[];
extern uint8_t g_ojo_run_offsets[];
extern uint8_t g_ojo_shadow_offsets[];
extern uint8_t g_ojo_shadow_bounds[];
extern uint8_t g_exvoto_frame_offsets[];
extern uint8_t g_exvoto_frame_bounds[];
extern uint8_t g_exvoto_run_offsets[];
extern uint8_t g_exvoto_shadow_offsets[];
extern uint8_t g_exvoto_shadow_bounds[];
extern uint8_t g_exvoto_pray_stand_frame_offsets[];
extern uint8_t g_exvoto_pray_stand_frame_bounds[];
extern uint8_t g_exvoto_pray_stand_run_offsets[];
extern uint8_t g_exvoto_pray_stand_shadow_offsets[];
extern uint8_t g_exvoto_pray_stand_shadow_bounds[];
extern uint8_t g_exvoto_pray_kneel_frame_offsets[];
extern uint8_t g_exvoto_pray_kneel_frame_bounds[];
extern uint8_t g_exvoto_pray_kneel_run_offsets[];
extern uint8_t g_exvoto_pray_kneel_shadow_offsets[];
extern uint8_t g_exvoto_pray_kneel_shadow_bounds[];
extern uint8_t g_exvoto_stand_up_frame_offsets[];
extern uint8_t g_exvoto_stand_up_frame_bounds[];
extern uint8_t g_exvoto_stand_up_run_offsets[];
extern uint8_t g_exvoto_stand_up_shadow_offsets[];
extern uint8_t g_exvoto_stand_up_shadow_bounds[];
extern uint8_t g_abanderado_frame_offsets[];
extern uint8_t g_abanderado_frame_bounds[];
extern uint8_t g_abanderado_run_offsets[];
extern uint8_t g_abanderado_shadow_offsets[];
extern uint8_t g_abanderado_shadow_bounds[];
extern uint8_t g_monaguillo_frame_offsets[];
extern uint8_t g_monaguillo_frame_bounds[];
extern uint8_t g_monaguillo_run_offsets[];
extern uint8_t g_monaguillo_shadow_offsets[];
extern uint8_t g_monaguillo_shadow_bounds[];
extern uint8_t g_hero_crouch_walk_frames[];
extern uint8_t g_hero_crouch_walk_frame_offsets[];
extern uint8_t g_hero_crouch_walk_frame_bounds[];
extern uint8_t g_hero_crouch_walk_runs[];
extern uint8_t g_hero_crouch_walk_run_offsets[];
extern uint8_t g_hero_crouch_walk_shadow_masks[];
extern uint8_t g_hero_crouch_walk_shadow_offsets[];
extern uint8_t g_hero_crouch_walk_shadow_bounds[];
extern uint8_t g_exvoto_bebe_frame_offsets[];
extern uint8_t g_exvoto_bebe_frame_bounds[];
extern uint8_t g_exvoto_bebe_run_offsets[];
extern uint8_t g_exvoto_bebe_shadow_offsets[];
extern uint8_t g_exvoto_bebe_shadow_bounds[];
extern uint8_t g_campanero_frames[];
extern uint8_t g_campanero_frame_offsets[];
extern uint8_t g_campanero_frame_bounds[];
extern uint8_t g_campanero_runs[];
extern uint8_t g_campanero_run_offsets[];
extern uint8_t g_campanero_shadow_masks[];
extern uint8_t g_campanero_shadow_offsets[];
extern uint8_t g_campanero_shadow_bounds[];
extern uint8_t g_exvoto_parroco_run_frame_offsets[];
extern uint8_t g_exvoto_parroco_run_frame_bounds[];
extern uint8_t g_exvoto_parroco_run_run_offsets[];
extern uint8_t g_exvoto_parroco_run_shadow_offsets[];
extern uint8_t g_exvoto_parroco_run_shadow_bounds[];
extern uint8_t g_exvoto_super_monja_frame_offsets[];
extern uint8_t g_exvoto_super_monja_frame_bounds[];
extern uint8_t g_exvoto_super_monja_run_offsets[];
extern uint8_t g_exvoto_super_monja_shadow_offsets[];
extern uint8_t g_exvoto_super_monja_shadow_bounds[];
extern uint8_t g_exvoto_super_monja_pray_stand_frame_offsets[];
extern uint8_t g_exvoto_super_monja_pray_stand_frame_bounds[];
extern uint8_t g_exvoto_super_monja_pray_stand_run_offsets[];
extern uint8_t g_exvoto_super_monja_pray_stand_shadow_offsets[];
extern uint8_t g_exvoto_super_monja_pray_stand_shadow_bounds[];
extern uint8_t g_exvoto_super_monja_pray_kneel_frame_offsets[];
extern uint8_t g_exvoto_super_monja_pray_kneel_frame_bounds[];
extern uint8_t g_exvoto_super_monja_pray_kneel_run_offsets[];
extern uint8_t g_exvoto_super_monja_pray_kneel_shadow_offsets[];
extern uint8_t g_exvoto_super_monja_pray_kneel_shadow_bounds[];
extern uint8_t g_exvoto_super_monja_stand_up_frame_offsets[];
extern uint8_t g_exvoto_super_monja_stand_up_frame_bounds[];
extern uint8_t g_exvoto_super_monja_stand_up_run_offsets[];
extern uint8_t g_exvoto_super_monja_stand_up_shadow_offsets[];
extern uint8_t g_exvoto_super_monja_stand_up_shadow_bounds[];
extern uint8_t g_exvoto_arana_walk_frame_offsets[];
extern uint8_t g_exvoto_arana_walk_frame_bounds[];
extern uint8_t g_exvoto_arana_walk_run_offsets[];
extern uint8_t g_exvoto_arana_walk_shadow_offsets[];
extern uint8_t g_exvoto_arana_walk_shadow_bounds[];
extern uint8_t g_exvoto_arana_trans_frame_offsets[];
extern uint8_t g_exvoto_arana_trans_frame_bounds[];
extern uint8_t g_exvoto_arana_trans_run_offsets[];
extern uint8_t g_exvoto_arana_trans_shadow_offsets[];
extern uint8_t g_exvoto_arana_trans_shadow_bounds[];
extern uint8_t g_monaguillo_arana_walk_frame_offsets[];
extern uint8_t g_monaguillo_arana_walk_frame_bounds[];
extern uint8_t g_monaguillo_arana_walk_run_offsets[];
extern uint8_t g_monaguillo_arana_walk_shadow_offsets[];
extern uint8_t g_monaguillo_arana_walk_shadow_bounds[];
extern uint8_t g_monaguillo_arana_trans_frame_offsets[];
extern uint8_t g_monaguillo_arana_trans_frame_bounds[];
extern uint8_t g_monaguillo_arana_trans_run_offsets[];
extern uint8_t g_monaguillo_arana_trans_shadow_offsets[];
extern uint8_t g_monaguillo_arana_trans_shadow_bounds[];
extern uint8_t g_charger_charge_frame_offsets[];
extern uint8_t g_charger_charge_frame_bounds[];
extern uint8_t g_charger_charge_run_offsets[];
extern uint8_t g_charger_charge_shadow_offsets[];
extern uint8_t g_charger_charge_shadow_bounds[];
extern uint8_t g_charger_telegraph_frame_offsets[];
extern uint8_t g_charger_telegraph_frame_bounds[];
extern uint8_t g_charger_telegraph_run_offsets[];
extern uint8_t g_ojo_look_frame_offsets[];
extern uint8_t g_ojo_look_frame_bounds[];
extern uint8_t g_ojo_look_run_offsets[];
extern uint8_t g_ojo_look_shadow_offsets[];
extern uint8_t g_ojo_look_shadow_bounds[];
extern uint8_t g_ojo_sentence_frame_offsets[];
extern uint8_t g_ojo_sentence_frame_bounds[];
extern uint8_t g_ojo_sentence_run_offsets[];
extern uint8_t g_ojo_sentence_shadow_offsets[];
extern uint8_t g_ojo_sentence_shadow_bounds[];
extern uint8_t g_player_shot_frames[];
extern uint8_t g_player_shot_frame_offsets[];
extern uint8_t g_player_shot_frame_bounds[];
extern uint8_t g_player_shot_runs[];
extern uint8_t g_player_shot_run_offsets[];
extern uint8_t g_player_shot_shadow_masks[];
extern uint8_t g_player_shot_shadow_offsets[];
extern uint8_t g_player_shot_shadow_bounds[];
extern uint8_t g_abanderado_point_frame_offsets[];
extern uint8_t g_abanderado_point_frame_bounds[];
extern uint8_t g_abanderado_point_run_offsets[];
extern uint8_t g_abanderado_point_shadow_offsets[];
extern uint8_t g_abanderado_point_shadow_bounds[];

const RoomLightSlot g_room_light_slots[] = {
    { g_player_frames, 64104 },
    { g_player_frame_offsets, 256 },
    { g_player_frame_bounds, 256 },
    { g_player_runs, 8888 },
    { g_player_run_offsets, 256 },
    { g_player_shadow_masks, 9263 },
    { g_player_shadow_offsets, 256 },
    { g_player_shadow_bounds, 256 },
    { g_charger_frame_offsets, 256 },
    { g_charger_frame_bounds, 256 },
    { g_charger_run_offsets, 256 },
    { g_charger_shadow_offsets, 256 },
    { g_charger_shadow_bounds, 256 },
    { g_ojo_frame_offsets, 256 },
    { g_ojo_frame_bounds, 256 },
    { g_ojo_run_offsets, 256 },
    { g_ojo_shadow_offsets, 256 },
    { g_ojo_shadow_bounds, 256 },
    { g_exvoto_frame_offsets, 256 },
    { g_exvoto_frame_bounds, 256 },
    { g_exvoto_run_offsets, 256 },
    { g_exvoto_shadow_offsets, 256 },
    { g_exvoto_shadow_bounds, 256 },
    { g_exvoto_pray_stand_frame_offsets, 256 },
    { g_exvoto_pray_stand_frame_bounds, 256 },
    { g_exvoto_pray_stand_run_offsets, 256 },
    { g_exvoto_pray_stand_shadow_offsets, 256 },
    { g_exvoto_pray_stand_shadow_bounds, 256 },
    { g_exvoto_pray_kneel_frame_offsets, 256 },
    { g_exvoto_pray_kneel_frame_bounds, 256 },
    { g_exvoto_pray_kneel_run_offsets, 256 },
    { g_exvoto_pray_kneel_shadow_offsets, 256 },
    { g_exvoto_pray_kneel_shadow_bounds, 256 },
    { g_exvoto_stand_up_frame_offsets, 256 },
    { g_exvoto_stand_up_frame_bounds, 256 },
    { g_exvoto_stand_up_run_offsets, 256 },
    { g_exvoto_stand_up_shadow_offsets, 256 },
    { g_exvoto_stand_up_shadow_bounds, 256 },
    { g_abanderado_frame_offsets, 256 },
    { g_abanderado_frame_bounds, 256 },
    { g_abanderado_run_offsets, 256 },
    { g_abanderado_shadow_offsets, 256 },
    { g_abanderado_shadow_bounds, 256 },
    { g_monaguillo_frame_offsets, 256 },
    { g_monaguillo_frame_bounds, 256 },
    { g_monaguillo_run_offsets, 256 },
    { g_monaguillo_shadow_offsets, 256 },
    { g_monaguillo_shadow_bounds, 256 },
    { g_hero_crouch_walk_frames, 47072 },
    { g_hero_crouch_walk_frame_offsets, 256 },
    { g_hero_crouch_walk_frame_bounds, 256 },
    { g_hero_crouch_walk_runs, 5952 },
    { g_hero_crouch_walk_run_offsets, 256 },
    { g_hero_crouch_walk_shadow_masks, 4959 },
    { g_hero_crouch_walk_shadow_offsets, 256 },
    { g_hero_crouch_walk_shadow_bounds, 256 },
    { g_exvoto_bebe_frame_offsets, 256 },
    { g_exvoto_bebe_frame_bounds, 256 },
    { g_exvoto_bebe_run_offsets, 256 },
    { g_exvoto_bebe_shadow_offsets, 256 },
    { g_exvoto_bebe_shadow_bounds, 256 },
    { g_campanero_frames, 2 },
    { g_campanero_frame_offsets, 256 },
    { g_campanero_frame_bounds, 256 },
    { g_campanero_runs, 2 },
    { g_campanero_run_offsets, 256 },
    { g_campanero_shadow_masks, 1 },
    { g_campanero_shadow_offsets, 256 },
    { g_campanero_shadow_bounds, 256 },
    { g_exvoto_parroco_run_frame_offsets, 256 },
    { g_exvoto_parroco_run_frame_bounds, 256 },
    { g_exvoto_parroco_run_run_offsets, 256 },
    { g_exvoto_parroco_run_shadow_offsets, 256 },
    { g_exvoto_parroco_run_shadow_bounds, 256 },
    { g_exvoto_super_monja_frame_offsets, 256 },
    { g_exvoto_super_monja_frame_bounds, 256 },
    { g_exvoto_super_monja_run_offsets, 256 },
    { g_exvoto_super_monja_shadow_offsets, 256 },
    { g_exvoto_super_monja_shadow_bounds, 256 },
    { g_exvoto_super_monja_pray_stand_frame_offsets, 256 },
    { g_exvoto_super_monja_pray_stand_frame_bounds, 256 },
    { g_exvoto_super_monja_pray_stand_run_offsets, 256 },
    { g_exvoto_super_monja_pray_stand_shadow_offsets, 256 },
    { g_exvoto_super_monja_pray_stand_shadow_bounds, 256 },
    { g_exvoto_super_monja_pray_kneel_frame_offsets, 256 },
    { g_exvoto_super_monja_pray_kneel_frame_bounds, 256 },
    { g_exvoto_super_monja_pray_kneel_run_offsets, 256 },
    { g_exvoto_super_monja_pray_kneel_shadow_offsets, 256 },
    { g_exvoto_super_monja_pray_kneel_shadow_bounds, 256 },
    { g_exvoto_super_monja_stand_up_frame_offsets, 256 },
    { g_exvoto_super_monja_stand_up_frame_bounds, 256 },
    { g_exvoto_super_monja_stand_up_run_offsets, 256 },
    { g_exvoto_super_monja_stand_up_shadow_offsets, 256 },
    { g_exvoto_super_monja_stand_up_shadow_bounds, 256 },
    { g_exvoto_arana_walk_frame_offsets, 256 },
    { g_exvoto_arana_walk_frame_bounds, 256 },
    { g_exvoto_arana_walk_run_offsets, 256 },
    { g_exvoto_arana_walk_shadow_offsets, 256 },
    { g_exvoto_arana_walk_shadow_bounds, 256 },
    { g_exvoto_arana_trans_frame_offsets, 256 },
    { g_exvoto_arana_trans_frame_bounds, 256 },
    { g_exvoto_arana_trans_run_offsets, 256 },
    { g_exvoto_arana_trans_shadow_offsets, 256 },
    { g_exvoto_arana_trans_shadow_bounds, 256 },
    { g_monaguillo_arana_walk_frame_offsets, 256 },
    { g_monaguillo_arana_walk_frame_bounds, 256 },
    { g_monaguillo_arana_walk_run_offsets, 256 },
    { g_monaguillo_arana_walk_shadow_offsets, 256 },
    { g_monaguillo_arana_walk_shadow_bounds, 256 },
    { g_monaguillo_arana_trans_frame_offsets, 256 },
    { g_monaguillo_arana_trans_frame_bounds, 256 },
    { g_monaguillo_arana_trans_run_offsets, 256 },
    { g_monaguillo_arana_trans_shadow_offsets, 256 },
    { g_monaguillo_arana_trans_shadow_bounds, 256 },
    { g_charger_charge_frame_offsets, 128 },
    { g_charger_charge_frame_bounds, 128 },
    { g_charger_charge_run_offsets, 128 },
    { g_charger_charge_shadow_offsets, 128 },
    { g_charger_charge_shadow_bounds, 128 },
    { g_charger_telegraph_frame_offsets, 32 },
    { g_charger_telegraph_frame_bounds, 32 },
    { g_charger_telegraph_run_offsets, 32 },
    { g_ojo_look_frame_offsets, 128 },
    { g_ojo_look_frame_bounds, 128 },
    { g_ojo_look_run_offsets, 128 },
    { g_ojo_look_shadow_offsets, 128 },
    { g_ojo_look_shadow_bounds, 128 },
    { g_ojo_sentence_frame_offsets, 192 },
    { g_ojo_sentence_frame_bounds, 192 },
    { g_ojo_sentence_run_offsets, 192 },
    { g_ojo_sentence_shadow_offsets, 192 },
    { g_ojo_sentence_shadow_bounds, 192 },
    { g_player_shot_frames, 89768 },
    { g_player_shot_frame_offsets, 256 },
    { g_player_shot_frame_bounds, 256 },
    { g_player_shot_runs, 9848 },
    { g_player_shot_run_offsets, 256 },
    { g_player_shot_shadow_masks, 10201 },
    { g_player_shot_shadow_offsets, 256 },
    { g_player_shot_shadow_bounds, 256 },
    { g_abanderado_point_frame_offsets, 256 },
    { g_abanderado_point_frame_bounds, 256 },
    { g_abanderado_point_run_offsets, 256 },
    { g_abanderado_point_shadow_offsets, 256 },
    { g_abanderado_point_shadow_bounds, 256 },
};
const uint32_t g_room_light_slot_count = 145;
