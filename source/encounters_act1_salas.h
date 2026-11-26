// Generado por tools/encuentros/gen_salas_rom.py desde tools/poster/salas/sala_NN.py. No editar a mano.
// Colocacion del poster por sala y bloque: piezas (en el tile exacto; sus estampas van en nitrofiles/rooms/sala_NN.rmk),
// rects de colision de sacos / alambre y miembros de cada grupo. Se incluye desde encounters_act1.c tras encounters_act1_tables.h.

typedef struct { uint8_t type, state; int16_t x, y; } RoomMember;     // ENC_E_*, ENC_S_*; x, y = pies, locales al bloque
typedef struct {
    const EncPieceDef *pieces; uint8_t n_pieces;
    const EncRectDef *rects; uint8_t n_rects;
    const RoomMember *members; uint8_t n_members;
} RoomLayout;

static const EncPieceDef s_r00_b0_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 48 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 240 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 280 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 320 },
};
static const RoomMember s_r00_b0_m[] = {
    { ENC_E_BEBE, ENC_S_CRAWL, 64, 160 },
    { ENC_E_BEBE, ENC_S_CRAWL, 96, 190 },
    { ENC_E_BEBE, ENC_S_CRAWL, 134, 168 },
    { ENC_E_BEBE, ENC_S_GUARD, 152, 214 },
    { ENC_E_BEBE, ENC_S_CRAWL, 80, 222 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 50 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 79 },
};
static const EncPieceDef s_r00_b1_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 8 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 48 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 240 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 320 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 96, 232 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 96, 272 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 96, 312 },
};
static const RoomMember s_r00_b1_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 118, 110 },
    { ENC_E_BEBE, ENC_S_CRAWL, 62, 150 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 196 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 170 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 262 },
};
static const EncPieceDef s_r00_b2_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 8 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 48 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 240 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 320 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 48 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 240 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 280 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 320 },
};
static const RoomMember s_r00_b2_m[] = {
    { ENC_E_MONAGUILLO, ENC_S_PATROL, 98, 100 },
    { ENC_E_MONAGUILLO, ENC_S_PATROL, 112, 128 },
    { ENC_E_BEBE, ENC_S_CRAWL, 92, 160 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 184 },
    { ENC_E_BEBE, ENC_S_GUARD, 98, 208 },
    { ENC_E_BEBE, ENC_S_CRAWL, 114, 232 },
    { ENC_E_BEBE, ENC_S_CRAWL, 102, 262 },
};
static const EncPieceDef s_r01_b0_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 8 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 48 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 48 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 240 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 280 },
    { STRIP_PIECE_SACOS_B, 72, 352 },
};
static const EncRectDef s_r01_b0_r[] = {
    { ENC_R_SACOS, 72, 360, 64, 8 },
};
static const RoomMember s_r01_b0_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 150, 92 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 80, 140 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 130, 152 },
    { ENC_E_BEBE, ENC_S_CRAWL, 62, 186 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 208 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 200 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 50 },
};
static const EncPieceDef s_r01_b1_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 40 },
    { STRIP_PIECE_BANCO_ENTERO, 16, 240 },
    { STRIP_PIECE_BANCO_ENTERO, 16, 280 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 96, 256 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 96, 304 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 344 },
    { STRIP_PIECE_BANCO_ROTO, 16, 320 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 48 },
};
static const RoomMember s_r01_b1_m[] = {
    { ENC_E_CIRENEO, ENC_S_STROLL, 104, 102 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 34 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 80, 150 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 132, 160 },
    { ENC_E_BEBE, ENC_S_CRAWL, 60, 192 },
    { ENC_E_BEBE, ENC_S_GUARD, 140, 198 },
    { ENC_E_BEBE, ENC_S_CRAWL, 172, 172 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 258 },
};
static const EncPieceDef s_r01_b2_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 40 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 320 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 240 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 280 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 112, 320 },
    { STRIP_PIECE_BANCO_ROTO, 8, 240 },
    { STRIP_PIECE_BANCO_ROTO, 8, 280 },
};
static const RoomMember s_r01_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 34 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 78, 138 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 128, 146 },
    { ENC_E_BEBE, ENC_S_CRAWL, 50, 190 },
    { ENC_E_BEBE, ENC_S_CRAWL, 94, 204 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 192 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 52 },
};
static const EncPieceDef s_r02_b0_p[] = {
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 144, 8 },
    { STRIP_PIECE_BANCO_ENTERO | STRIP_PIECE_MIRROR, 144, 272 },
    { STRIP_PIECE_BANCO_ROTO, 8, 8 },
    { STRIP_PIECE_SACOS_B, 80, 336 },
};
static const EncRectDef s_r02_b0_r[] = {
    { ENC_R_SACOS, 80, 344, 64, 8 },
};
static const RoomMember s_r02_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 79 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 34 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 70, 136 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 110, 128 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 146, 140 },
    { ENC_E_BEBE, ENC_S_CRAWL, 32, 176 },
    { ENC_E_BEBE, ENC_S_CRAWL, 90, 200 },
    { ENC_E_BEBE, ENC_S_GUARD, 132, 190 },
    { ENC_E_BEBE, ENC_S_CRAWL, 160, 215 },
};
static const EncPieceDef s_r02_b1_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 8 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 40 },
    { STRIP_PIECE_BANCO_ENTERO, 16, 312 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 344 },
    { STRIP_PIECE_BANCO_ROTO, 16, 272 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 56 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 344 },
    { STRIP_PIECE_BANCO_VOLCADO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_SACOS, 128, 248 },
};
static const EncRectDef s_r02_b1_r[] = {
    { ENC_R_SACOS, 128, 268, 64, 4 },
};
static const RoomMember s_r02_b1_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 30, 104 },
    { ENC_E_OJO, ENC_S_GUARD, 178, 108 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 36 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 82, 150 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 130, 160 },
    { ENC_E_BEBE, ENC_S_CRAWL, 60, 200 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 206 },
    { ENC_E_BEBE, ENC_S_CRAWL, 118, 226 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 264 },
};
static const EncPieceDef s_r02_b2_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 8, 8 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 40 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 40 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 240 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 280 },
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 320 },
    { STRIP_PIECE_BANCO_VOLCADO, 8, 240 },
    { STRIP_PIECE_COLUMNA_ROTA, 0, 288 },
};
static const RoomMember s_r02_b2_m[] = {
    { ENC_E_CIRENEO, ENC_S_STROLL, 58, 112 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 150, 122 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 34 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 92, 160 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 122, 172 },
    { ENC_E_BEBE, ENC_S_CRAWL, 70, 200 },
    { ENC_E_BEBE, ENC_S_GUARD, 160, 196 },
    { ENC_E_BEBE, ENC_S_CRAWL, 106, 266 },
};
static const EncPieceDef s_r03_b0_p[] = {
    { STRIP_PIECE_ALAMBRE, 104, 232 },
    { STRIP_PIECE_BANCO_ROTO, 8, 8 },
    { STRIP_PIECE_BANCO_VOLCADO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_SACOS, 96, 336 },
};
static const EncRectDef s_r03_b0_r[] = {
    { ENC_R_ALAMBRE, 104, 240, 32, 16 },
    { ENC_R_SACOS, 96, 356, 64, 4 },
};
static const RoomMember s_r03_b0_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 104, 88 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 64 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 79 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 52, 150 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 90, 140 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 120, 150 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 152, 136 },
    { ENC_E_BEBE, ENC_S_CRAWL, 60, 204 },
    { ENC_E_BEBE, ENC_S_GUARD, 140, 202 },
    { ENC_E_BEBE, ENC_S_CRAWL, 170, 178 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 46 },
};
static const EncPieceDef s_r03_b1_p[] = {
    { STRIP_PIECE_BANCO_ROTO | STRIP_PIECE_MIRROR, 112, 344 },
    { STRIP_PIECE_BANCO_VOLCADO, 8, 8 },
    { STRIP_PIECE_BANCO_VOLCADO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_COLUMNA_ROTA, 0, 232 },
    { STRIP_PIECE_SACOS, 72, 232 },
};
static const EncRectDef s_r03_b1_r[] = {
    { ENC_R_SACOS, 72, 252, 64, 4 },
};
static const RoomMember s_r03_b1_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 28, 122 },
    { ENC_E_OJO, ENC_S_GUARD, 180, 128 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 64 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 80, 150 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 110, 142 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 136, 156 },
    { ENC_E_BEBE, ENC_S_CRAWL, 50, 196 },
    { ENC_E_BEBE, ENC_S_GUARD, 130, 200 },
    { ENC_E_BEBE, ENC_S_CRAWL, 160, 212 },
    { ENC_E_BEBE, ENC_S_CRAWL, 170, 178 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 270 },
};
static const EncPieceDef s_r03_b2_p[] = {
    { STRIP_PIECE_ALAMBRE, 96, 344 },
    { STRIP_PIECE_BANCO_ENTERO, 8, 240 },
    { STRIP_PIECE_BANCO_ROTO, 0, 56 },
    { STRIP_PIECE_BANCO_ROTO, 8, 344 },
    { STRIP_PIECE_BANCO_VOLCADO, 8, 296 },
    { STRIP_PIECE_BANCO_VOLCADO | STRIP_PIECE_MIRROR, 112, 8 },
    { STRIP_PIECE_SACOS_B, 128, 232 },
};
static const EncRectDef s_r03_b2_r[] = {
    { ENC_R_ALAMBRE, 96, 352, 32, 16 },
    { ENC_R_SACOS, 128, 240, 64, 8 },
};
static const RoomMember s_r03_b2_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 182, 112 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 34 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 150, 79 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 50, 132 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 156, 152 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 88, 168 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 118, 160 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 138, 188 },
    { ENC_E_BEBE, ENC_S_CRAWL, 60, 204 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 216 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 224 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 46, 61 },
};
static const EncPieceDef s_r04_b0_p[] = {
    { STRIP_PIECE_CEPO, 0, 0 },
    { STRIP_PIECE_CEPO, 0, 48 },
    { STRIP_PIECE_CEPO, 0, 96 },
    { STRIP_PIECE_CEPO, 0, 288 },
    { STRIP_PIECE_CEPO, 0, 336 },
    { STRIP_PIECE_SACOS, 136, 24 },
    { STRIP_PIECE_SACOS, 136, 64 },
    { STRIP_PIECE_SACOS, 128, 152 },
    { STRIP_PIECE_SACOS, 128, 256 },
    { STRIP_PIECE_SACOS, 128, 304 },
    { STRIP_PIECE_SACOS_B, 128, 0 },
    { STRIP_PIECE_SACOS_B, 128, 176 },
    { STRIP_PIECE_SACOS_B, 128, 280 },
    { STRIP_PIECE_SACOS_B, 128, 328 },
};
static const EncRectDef s_r04_b0_r[] = {
    { ENC_R_SACOS, 136, 44, 64, 4 },
    { ENC_R_SACOS, 136, 84, 64, 4 },
    { ENC_R_SACOS, 128, 172, 64, 4 },
    { ENC_R_SACOS, 128, 276, 64, 4 },
    { ENC_R_SACOS, 128, 324, 64, 4 },
    { ENC_R_SACOS, 128, 8, 64, 8 },
    { ENC_R_SACOS, 128, 184, 64, 8 },
    { ENC_R_SACOS, 128, 288, 64, 8 },
    { ENC_R_SACOS, 128, 336, 64, 8 },
};
static const RoomMember s_r04_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 60, 84 },
    { ENC_E_BEBE, ENC_S_CRAWL, 40, 140 },
    { ENC_E_BEBE, ENC_S_GUARD, 56, 154 },
    { ENC_E_BEBE, ENC_S_CRAWL, 36, 166 },
    { ENC_E_BEBE, ENC_S_CRAWL, 98, 122 },
    { ENC_E_BEBE, ENC_S_CRAWL, 124, 144 },
    { ENC_E_BEBE, ENC_S_GUARD, 152, 126 },
};
static const EncPieceDef s_r05_b0_p[] = {
    { STRIP_PIECE_CAPULLO, 0, 0 },
    { STRIP_PIECE_CAPULLO, 48, 232 },
    { STRIP_PIECE_CAPULLO, 16, 248 },
    { STRIP_PIECE_SACOS, 16, 312 },
    { STRIP_PIECE_SACOS_B, 80, 312 },
    { STRIP_PIECE_SACOS_B, 0, 352 },
    { STRIP_PIECE_SACOS_REMATE, 144, 352 },
};
static const EncRectDef s_r05_b0_r[] = {
    { ENC_R_SACOS, 16, 332, 64, 4 },
    { ENC_R_SACOS, 80, 320, 64, 8 },
    { ENC_R_SACOS, 0, 360, 64, 8 },
    { ENC_R_SACOS, 144, 364, 64, 4 },
};
static const RoomMember s_r05_b0_m[] = {
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 150, 98 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 150, 140 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 138 },
    { ENC_E_BEBE, ENC_S_CRAWL, 96, 162 },
    { ENC_E_BEBE, ENC_S_GUARD, 128, 170 },
    { ENC_E_BEBE, ENC_S_CRAWL, 160, 178 },
    { ENC_E_BEBE, ENC_S_CRAWL, 122, 112 },
};
static const EncPieceDef s_r06_b0_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 16, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 16, 168 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 168 },
};
static const RoomMember s_r06_b0_m[] = {
    { ENC_E_BEBE, ENC_S_CRAWL, 150, 142 },
    { ENC_E_BEBE, ENC_S_GUARD, 164, 154 },
    { ENC_E_BEBE, ENC_S_CRAWL, 144, 158 },
    { ENC_E_BEBE, ENC_S_CRAWL, 157, 168 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 112 },
    { ENC_E_BEBE, ENC_S_CRAWL, 98, 130 },
    { ENC_E_BEBE, ENC_S_GUARD, 70, 140 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 96, 16 },
};
static const EncPieceDef s_r06_b1_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 168 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 168 },
};
static const RoomMember s_r06_b1_m[] = {
    { ENC_E_MONAGUILLO, ENC_S_PATROL, 70, 150 },
    { ENC_E_MONAGUILLO, ENC_S_PATROL, 125, 262 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 35, 108 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 155, 108 },
    { ENC_E_BEBE, ENC_S_CRAWL, 62, 198 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 214 },
    { ENC_E_BEBE, ENC_S_CRAWL, 88, 246 },
};
static const EncPieceDef s_r06_b2_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 120, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 168 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 176 },
};
static const RoomMember s_r06_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 118, 122 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 94, 110 },
    { ENC_E_BEBE, ENC_S_CRAWL, 74, 176 },
    { ENC_E_BEBE, ENC_S_CRAWL, 100, 198 },
    { ENC_E_BEBE, ENC_S_GUARD, 118, 160 },
    { ENC_E_BEBE, ENC_S_CRAWL, 86, 142 },
};
static const EncPieceDef s_r07_b0_p[] = {
    { STRIP_PIECE_BANCO_ROTO, 72, 336 },
    { STRIP_PIECE_COLUMNA_ENTERA, 16, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 16, 168 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 168 },
};
static const RoomMember s_r07_b0_m[] = {
    { ENC_E_OJO, ENC_S_SWEEP, 98, 66 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 64, 104 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 122, 98 },
    { ENC_E_BEBE, ENC_S_CRAWL, 90, 140 },
    { ENC_E_BEBE, ENC_S_CRAWL, 116, 153 },
    { ENC_E_BEBE, ENC_S_GUARD, 76, 126 },
    { ENC_E_BEBE, ENC_S_CRAWL, 124, 144 },
};
static const EncPieceDef s_r07_b1_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 168 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 168 },
    { STRIP_PIECE_LAPIDA_PIE, 88, 336 },
};
static const RoomMember s_r07_b1_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 96, 52 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 68, 92 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 126, 84 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 112, 232 },
    { ENC_E_BEBE, ENC_S_CRAWL, 70, 205 },
    { ENC_E_BEBE, ENC_S_CRAWL, 96, 188 },
    { ENC_E_BEBE, ENC_S_CRAWL, 84, 228 },
    { ENC_E_BEBE, ENC_S_GUARD, 100, 160 },
};
static const EncPieceDef s_r07_b2_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 8 },
    { STRIP_PIECE_COLUMNA_ENTERA, 120, 16 },
    { STRIP_PIECE_COLUMNA_ENTERA, 8, 168 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 168 },
};
static const RoomMember s_r07_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 60, 58 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 62, 104 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 70, 150 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 122, 146 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 150, 106 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 160, 111 },
    { ENC_E_BEBE, ENC_S_CRAWL, 82, 192 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 208 },
};
static const EncPieceDef s_r08_b0_p[] = {
    { STRIP_PIECE_BIOMBO, 0, 328 },
    { STRIP_PIECE_CANDELABRO_PIE, 56, 24 },
    { STRIP_PIECE_CATRE, 0, 16 },
    { STRIP_PIECE_CATRE, 0, 232 },
    { STRIP_PIECE_CATRE, 0, 280 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 16 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 144, 248 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 144, 296 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 336 },
    { STRIP_PIECE_PALANGANA, 48, 248 },
};
static const RoomMember s_r08_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 34, 82 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 84, 74 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 26, 128 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 76, 132 },
    { ENC_E_BEBE, ENC_S_GUARD, 152, 96 },
    { ENC_E_BEBE, ENC_S_CRAWL, 178, 128 },
    { ENC_E_BEBE, ENC_S_CRAWL, 118, 178 },
    { ENC_E_BEBE, ENC_S_GUARD, 58, 196 },
};
static const EncPieceDef s_r08_b1_p[] = {
    { STRIP_PIECE_BIOMBO | STRIP_PIECE_MIRROR, 152, 328 },
    { STRIP_PIECE_CANDELABRO_PIE, 120, 16 },
    { STRIP_PIECE_CATRE, 0, 16 },
    { STRIP_PIECE_CATRE, 0, 232 },
    { STRIP_PIECE_CATRE, 0, 280 },
    { STRIP_PIECE_CATRE, 0, 328 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 16 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 232 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 280 },
    { STRIP_PIECE_PALANGANA, 48, 248 },
};
static const RoomMember s_r08_b1_m[] = {
    { ENC_E_OJO, ENC_S_SWEEP, 100, 80 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 60, 128 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 142, 122 },
    { ENC_E_BEBE, ENC_S_CRAWL, 50, 176 },
    { ENC_E_BEBE, ENC_S_GUARD, 112, 190 },
    { ENC_E_BEBE, ENC_S_CRAWL, 150, 168 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 162, 355 },
};
static const EncPieceDef s_r08_b2_p[] = {
    { STRIP_PIECE_CATRE, 0, 16 },
    { STRIP_PIECE_CATRE, 16, 248 },
    { STRIP_PIECE_CATRE, 16, 296 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 16 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 232 },
    { STRIP_PIECE_CATRE | STRIP_PIECE_MIRROR, 160, 280 },
};
static const RoomMember s_r08_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 82 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 138, 112 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 182, 120 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 72, 158 },
    { ENC_E_BEBE, ENC_S_GUARD, 60, 100 },
    { ENC_E_BEBE, ENC_S_CRAWL, 100, 130 },
    { ENC_E_BEBE, ENC_S_GUARD, 124, 194 },
    { ENC_E_BEBE, ENC_S_CRAWL, 152, 204 },
};
static const EncPieceDef s_r09_b0_p[] = {
    { STRIP_PIECE_CALAVERAS_PILA, 168, 112 },
    { STRIP_PIECE_CALAVERAS_PILA, 136, 344 },
    { STRIP_PIECE_HUESOS_MONTON, 40, 304 },
    { STRIP_PIECE_OSARIO_LADO, 160, 0 },
    { STRIP_PIECE_OSARIO_LADO, 160, 240 },
    { STRIP_PIECE_OSARIO_LADO, 160, 288 },
    { STRIP_PIECE_OSARIO_LADO, 160, 336 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 0 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 192 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 240 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 288 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 336 },
};
static const RoomMember s_r09_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 28, 70 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 66, 62 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 102, 72 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 34, 120 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 80, 126 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 126, 118 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 180, 113 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 195, 116 },
    { ENC_E_BEBE, ENC_S_CRAWL, 100, 168 },
    { ENC_E_BEBE, ENC_S_GUARD, 52, 178 },
};
static const EncPieceDef s_r09_b1_p[] = {
    { STRIP_PIECE_CALAVERAS_PILA, 16, 80 },
    { STRIP_PIECE_HUESOS_MONTON, 168, 160 },
    { STRIP_PIECE_OSARIO_LADO, 160, 0 },
    { STRIP_PIECE_OSARIO_LADO, 160, 192 },
    { STRIP_PIECE_OSARIO_LADO, 160, 240 },
    { STRIP_PIECE_OSARIO_LADO, 160, 288 },
    { STRIP_PIECE_OSARIO_LADO, 160, 336 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 0 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 8, 240 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 8, 288 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 336 },
};
static const RoomMember s_r09_b1_m[] = {
    { ENC_E_OJO, ENC_S_SWEEP, 30, 76 },
    { ENC_E_OJO, ENC_S_SWEEP, 180, 150 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 98, 66 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 72, 118 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 134, 104 },
    { ENC_E_BEBE, ENC_S_HIDDEN, 27, 118 },
    { ENC_E_BEBE, ENC_S_GUARD, 138, 182 },
    { ENC_E_BEBE, ENC_S_CRAWL, 62, 172 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 160 },
};
static const EncPieceDef s_r09_b2_p[] = {
    { STRIP_PIECE_CALAVERAS_PILA, 40, 40 },
    { STRIP_PIECE_CALAVERAS_PILA, 144, 40 },
    { STRIP_PIECE_OSARIO_ESTANTE, 8, 0 },
    { STRIP_PIECE_OSARIO_ESTANTE, 56, 0 },
    { STRIP_PIECE_OSARIO_ESTANTE, 104, 0 },
    { STRIP_PIECE_OSARIO_ESTANTE, 152, 0 },
    { STRIP_PIECE_OSARIO_LADO, 160, 192 },
    { STRIP_PIECE_OSARIO_LADO, 160, 240 },
    { STRIP_PIECE_OSARIO_LADO, 160, 288 },
    { STRIP_PIECE_OSARIO_LADO, 160, 336 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 192 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 240 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 288 },
    { STRIP_PIECE_OSARIO_LADO | STRIP_PIECE_MIRROR, 0, 336 },
};
static const RoomMember s_r09_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 28, 90 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 52, 122 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 160, 112 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 68, 164 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 142, 176 },
    { ENC_E_BEBE, ENC_S_GUARD, 100, 130 },
    { ENC_E_BEBE, ENC_S_CRAWL, 120, 152 },
    { ENC_E_BEBE, ENC_S_CRAWL, 178, 150 },
};
static const EncPieceDef s_r10_b0_p[] = {
    { STRIP_PIECE_ALTAR_PIE, 96, 8 },
    { STRIP_PIECE_CANDELABRO_PIE, 56, 8 },
    { STRIP_PIECE_CANDELABRO_PIE, 120, 8 },
    { STRIP_PIECE_RECLINATORIO, 8, 248 },
    { STRIP_PIECE_RECLINATORIO, 160, 248 },
    { STRIP_PIECE_RECLINATORIO, 8, 296 },
    { STRIP_PIECE_RECLINATORIO, 160, 296 },
    { STRIP_PIECE_RELICARIO, 16, 16 },
    { STRIP_PIECE_RELICARIO, 152, 16 },
};
static const RoomMember s_r10_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 26, 106 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 52, 90 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 40, 130 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 68, 112 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 144, 108 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 168, 94 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 150, 132 },
    { ENC_E_PARROCO, ENC_S_GUARD, 108, 56 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 58, 164 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 94, 172 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 128, 162 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 162, 170 },
};
static const EncPieceDef s_r11_b0_p[] = {
    { STRIP_PIECE_RECLINATORIO, 8, 48 },
    { STRIP_PIECE_RECLINATORIO, 168, 48 },
    { STRIP_PIECE_RECLINATORIO, 8, 88 },
    { STRIP_PIECE_RECLINATORIO, 160, 88 },
    { STRIP_PIECE_RECLINATORIO, 8, 128 },
    { STRIP_PIECE_RECLINATORIO, 160, 128 },
    { STRIP_PIECE_RECLINATORIO, 8, 168 },
    { STRIP_PIECE_RECLINATORIO, 160, 168 },
    { STRIP_PIECE_RECLINATORIO, 8, 256 },
    { STRIP_PIECE_RECLINATORIO, 160, 256 },
    { STRIP_PIECE_RECLINATORIO, 8, 296 },
    { STRIP_PIECE_RECLINATORIO, 160, 296 },
    { STRIP_PIECE_RECLINATORIO, 8, 336 },
    { STRIP_PIECE_RECLINATORIO, 168, 336 },
};
static const EncPieceDef s_r11_b1_p[] = {
    { STRIP_PIECE_ALTAR_PIE, 96, 8 },
    { STRIP_PIECE_CANDELABRO_PIE, 56, 8 },
    { STRIP_PIECE_CANDELABRO_PIE, 120, 8 },
    { STRIP_PIECE_RECLINATORIO, 8, 240 },
    { STRIP_PIECE_RECLINATORIO, 168, 240 },
    { STRIP_PIECE_RECLINATORIO, 8, 296 },
    { STRIP_PIECE_RECLINATORIO, 160, 296 },
};
static const RoomMember s_r11_b1_m[] = {
    { ENC_E_PARROCO, ENC_S_GUARD, 90, 66 },
    { ENC_E_PARROCO, ENC_S_GUARD, 131, 62 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 76, 124 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 142, 164 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 106, 204 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 29, 301 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 178, 304 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 36, 366 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 170, 364 },
    { ENC_E_MONJA, ENC_S_HIDDEN, 26, 47 },
    { ENC_E_MONJA, ENC_S_HIDDEN, 171, 46 },
};
static const EncPieceDef s_r12_b0_p[] = {
    { STRIP_PIECE_ALAMBRE, 0, 344 },
    { STRIP_PIECE_ALAMBRE, 32, 344 },
    { STRIP_PIECE_ALAMBRE, 144, 344 },
    { STRIP_PIECE_ALAMBRE, 176, 344 },
    { STRIP_PIECE_CAPULLO, 24, 8 },
    { STRIP_PIECE_CAPULLO, 152, 8 },
    { STRIP_PIECE_CEPO, 16, 288 },
    { STRIP_PIECE_CEPO, 168, 288 },
};
static const EncRectDef s_r12_b0_r[] = {
    { ENC_R_ALAMBRE, 0, 352, 32, 16 },
    { ENC_R_ALAMBRE, 32, 352, 32, 16 },
    { ENC_R_ALAMBRE, 144, 352, 32, 16 },
    { ENC_R_ALAMBRE, 176, 352, 32, 16 },
};
static const RoomMember s_r12_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 40 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 84, 80 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 128, 76 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 140, 222 },
    { ENC_E_CIRENEO, ENC_S_STROLL, 100, 148 },
    { ENC_E_BEBE, ENC_S_CRAWL, 70, 118 },
    { ENC_E_BEBE, ENC_S_CRAWL, 118, 106 },
    { ENC_E_BEBE, ENC_S_GUARD, 90, 170 },
};
static const EncPieceDef s_r12_b1_p[] = {
    { STRIP_PIECE_ALAMBRE, 0, 352 },
    { STRIP_PIECE_ALAMBRE, 32, 352 },
    { STRIP_PIECE_ALAMBRE, 144, 352 },
    { STRIP_PIECE_ALAMBRE, 176, 352 },
    { STRIP_PIECE_CAPULLO, 24, 296 },
    { STRIP_PIECE_CAPULLO, 168, 296 },
    { STRIP_PIECE_CEPO, 8, 8 },
    { STRIP_PIECE_CEPO, 168, 8 },
};
static const EncRectDef s_r12_b1_r[] = {
    { ENC_R_ALAMBRE, 0, 360, 32, 16 },
    { ENC_R_ALAMBRE, 32, 360, 32, 16 },
    { ENC_R_ALAMBRE, 144, 360, 32, 16 },
    { ENC_R_ALAMBRE, 176, 360, 32, 16 },
};
static const RoomMember s_r12_b1_m[] = {
    { ENC_E_OJO, ENC_S_SWEEP, 30, 88 },
    { ENC_E_OJO, ENC_S_SWEEP, 178, 92 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 30 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 68, 76 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 146, 70 },
    { ENC_E_BEBE, ENC_S_CRAWL, 80, 170 },
    { ENC_E_BEBE, ENC_S_CRAWL, 112, 150 },
    { ENC_E_BEBE, ENC_S_GUARD, 142, 186 },
    { ENC_E_BEBE, ENC_S_CRAWL, 70, 216 },
};
static const EncPieceDef s_r13_b0_p[] = {
    { STRIP_PIECE_ALTAR_PIE, 40, 8 },
    { STRIP_PIECE_ALTAR_PIE, 152, 8 },
    { STRIP_PIECE_RECLINATORIO, 56, 256 },
    { STRIP_PIECE_RECLINATORIO, 168, 256 },
    { STRIP_PIECE_RECLINATORIO, 56, 296 },
    { STRIP_PIECE_RECLINATORIO, 168, 296 },
    { STRIP_PIECE_RELICARIO, 80, 0 },
};
static const RoomMember s_r13_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 82, 168 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 128, 161 },
    { ENC_E_OJO, ENC_S_SWEEP, 26, 174 },
    { ENC_E_OJO, ENC_S_SWEEP, 184, 178 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 64, 198 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 103, 204 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 142, 196 },
    { ENC_E_BEBE, ENC_S_CRAWL, 48, 228 },
    { ENC_E_BEBE, ENC_S_CRAWL, 86, 236 },
    { ENC_E_BEBE, ENC_S_CRAWL, 120, 224 },
    { ENC_E_BEBE, ENC_S_GUARD, 155, 240 },
    { ENC_E_BEBE, ENC_S_CRAWL, 104, 246 },
};
static const EncPieceDef s_r14_b0_p[] = {
    { STRIP_PIECE_CALAVERAS_PILA, 88, 208 },
    { STRIP_PIECE_CAPULLO, 64, 152 },
    { STRIP_PIECE_COLUMNA_ENTERA, 56, 0 },
    { STRIP_PIECE_COLUMNA_ENTERA, 112, 0 },
    { STRIP_PIECE_COLUMNA_ENTERA, 56, 256 },
    { STRIP_PIECE_COLUMNA_ENTERA, 112, 256 },
    { STRIP_PIECE_SANTO, 8, 8 },
    { STRIP_PIECE_SANTO, 16, 80 },
    { STRIP_PIECE_SANTO, 16, 264 },
    { STRIP_PIECE_SANTO_DER, 168, 8 },
    { STRIP_PIECE_SANTO_DER, 168, 80 },
    { STRIP_PIECE_SANTO_DER, 168, 152 },
    { STRIP_PIECE_SANTO_DER, 168, 264 },
};
static const EncPieceDef s_r14_b1_p[] = {
    { STRIP_PIECE_CAPULLO, 48, 0 },
    { STRIP_PIECE_CAPULLO, 56, 64 },
    { STRIP_PIECE_CAPULLO, 48, 256 },
    { STRIP_PIECE_CAPULLO, 64, 312 },
    { STRIP_PIECE_HUESOS_MONTON, 88, 184 },
    { STRIP_PIECE_SANTO, 8, 240 },
    { STRIP_PIECE_SANTO, 8, 312 },
    { STRIP_PIECE_SANTO_DER, 168, 0 },
    { STRIP_PIECE_SANTO_DER, 168, 240 },
    { STRIP_PIECE_SANTO_DER, 168, 312 },
};
static const RoomMember s_r14_b1_m[] = {
    { ENC_E_MONJA, ENC_S_HIDDEN, 95, 44 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 38, 112 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 99, 108 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 158, 118 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 66, 142 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 30, 178 },
    { ENC_E_MONAGUILLO, ENC_S_SWAY, 152, 182 },
    { ENC_E_MONAGUILLO, ENC_S_HIDDEN, 71, 285 },
    { ENC_E_MONAGUILLO, ENC_S_HIDDEN, 137, 288 },
};
static const EncPieceDef s_r15_b0_p[] = {
    { STRIP_PIECE_BRASERO, 16, 336 },
    { STRIP_PIECE_BRASERO, 152, 336 },
    { STRIP_PIECE_CALAVERAS_PILA, 48, 120 },
    { STRIP_PIECE_HUESOS_MONTON, 128, 280 },
    { STRIP_PIECE_LAPIDA_PIE, 8, 144 },
    { STRIP_PIECE_LAPIDA_PIE, 176, 144 },
    { STRIP_PIECE_LAPIDA_PIE, 8, 256 },
    { STRIP_PIECE_LAPIDA_PIE, 176, 256 },
    { STRIP_PIECE_SARCOFAGO, 72, 0 },
    { STRIP_PIECE_SARCOFAGO_LADO, 160, 80 },
    { STRIP_PIECE_SARCOFAGO_LADO, 160, 112 },
    { STRIP_PIECE_SARCOFAGO_LADO, 160, 192 },
    { STRIP_PIECE_SARCOFAGO_LADO, 160, 224 },
    { STRIP_PIECE_SARCOFAGO_LADO, 160, 304 },
    { STRIP_PIECE_SARCOFAGO_LADO | STRIP_PIECE_MIRROR, 0, 80 },
    { STRIP_PIECE_SARCOFAGO_LADO | STRIP_PIECE_MIRROR, 0, 112 },
    { STRIP_PIECE_SARCOFAGO_LADO | STRIP_PIECE_MIRROR, 0, 192 },
    { STRIP_PIECE_SARCOFAGO_LADO | STRIP_PIECE_MIRROR, 0, 224 },
    { STRIP_PIECE_SARCOFAGO_LADO | STRIP_PIECE_MIRROR, 0, 304 },
};

#define ENC_ARR_OR_0(a) (a), (uint8_t)(sizeof(a) / sizeof((a)[0]))
// [sala][bloque]: valid = 1 cuando el poster manda en ese bloque (piezas y rects aunque esten vacios; miembros si los hay)
static const struct { uint8_t valid; RoomLayout l; } s_room_layouts[ENC_ROOM_COUNT][ENC_STAGES] = {
    { // sala 0
        { 1, { ENC_ARR_OR_0(s_r00_b0_p), 0, 0, ENC_ARR_OR_0(s_r00_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r00_b1_p), 0, 0, ENC_ARR_OR_0(s_r00_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r00_b2_p), 0, 0, ENC_ARR_OR_0(s_r00_b2_m) } },
    },
    { // sala 1
        { 1, { ENC_ARR_OR_0(s_r01_b0_p), ENC_ARR_OR_0(s_r01_b0_r), ENC_ARR_OR_0(s_r01_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r01_b1_p), 0, 0, ENC_ARR_OR_0(s_r01_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r01_b2_p), 0, 0, ENC_ARR_OR_0(s_r01_b2_m) } },
    },
    { // sala 2
        { 1, { ENC_ARR_OR_0(s_r02_b0_p), ENC_ARR_OR_0(s_r02_b0_r), ENC_ARR_OR_0(s_r02_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r02_b1_p), ENC_ARR_OR_0(s_r02_b1_r), ENC_ARR_OR_0(s_r02_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r02_b2_p), 0, 0, ENC_ARR_OR_0(s_r02_b2_m) } },
    },
    { // sala 3
        { 1, { ENC_ARR_OR_0(s_r03_b0_p), ENC_ARR_OR_0(s_r03_b0_r), ENC_ARR_OR_0(s_r03_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r03_b1_p), ENC_ARR_OR_0(s_r03_b1_r), ENC_ARR_OR_0(s_r03_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r03_b2_p), ENC_ARR_OR_0(s_r03_b2_r), ENC_ARR_OR_0(s_r03_b2_m) } },
    },
    { // sala 4
        { 1, { ENC_ARR_OR_0(s_r04_b0_p), ENC_ARR_OR_0(s_r04_b0_r), ENC_ARR_OR_0(s_r04_b0_m) } },
        { 0 },
        { 0 },
    },
    { // sala 5
        { 1, { ENC_ARR_OR_0(s_r05_b0_p), ENC_ARR_OR_0(s_r05_b0_r), ENC_ARR_OR_0(s_r05_b0_m) } },
        { 0 },
        { 0 },
    },
    { // sala 6
        { 1, { ENC_ARR_OR_0(s_r06_b0_p), 0, 0, ENC_ARR_OR_0(s_r06_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r06_b1_p), 0, 0, ENC_ARR_OR_0(s_r06_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r06_b2_p), 0, 0, ENC_ARR_OR_0(s_r06_b2_m) } },
    },
    { // sala 7
        { 1, { ENC_ARR_OR_0(s_r07_b0_p), 0, 0, ENC_ARR_OR_0(s_r07_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r07_b1_p), 0, 0, ENC_ARR_OR_0(s_r07_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r07_b2_p), 0, 0, ENC_ARR_OR_0(s_r07_b2_m) } },
    },
    { // sala 8
        { 1, { ENC_ARR_OR_0(s_r08_b0_p), 0, 0, ENC_ARR_OR_0(s_r08_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r08_b1_p), 0, 0, ENC_ARR_OR_0(s_r08_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r08_b2_p), 0, 0, ENC_ARR_OR_0(s_r08_b2_m) } },
    },
    { // sala 9
        { 1, { ENC_ARR_OR_0(s_r09_b0_p), 0, 0, ENC_ARR_OR_0(s_r09_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r09_b1_p), 0, 0, ENC_ARR_OR_0(s_r09_b1_m) } },
        { 1, { ENC_ARR_OR_0(s_r09_b2_p), 0, 0, ENC_ARR_OR_0(s_r09_b2_m) } },
    },
    { // sala 10
        { 1, { ENC_ARR_OR_0(s_r10_b0_p), 0, 0, ENC_ARR_OR_0(s_r10_b0_m) } },
        { 0 },
        { 0 },
    },
    { // sala 11
        { 1, { ENC_ARR_OR_0(s_r11_b0_p), 0, 0, 0, 0 } },
        { 1, { ENC_ARR_OR_0(s_r11_b1_p), 0, 0, ENC_ARR_OR_0(s_r11_b1_m) } },
        { 0 },
    },
    { // sala 12
        { 1, { ENC_ARR_OR_0(s_r12_b0_p), ENC_ARR_OR_0(s_r12_b0_r), ENC_ARR_OR_0(s_r12_b0_m) } },
        { 1, { ENC_ARR_OR_0(s_r12_b1_p), ENC_ARR_OR_0(s_r12_b1_r), ENC_ARR_OR_0(s_r12_b1_m) } },
        { 0 },
    },
    { // sala 13
        { 1, { ENC_ARR_OR_0(s_r13_b0_p), 0, 0, ENC_ARR_OR_0(s_r13_b0_m) } },
        { 0 },
        { 0 },
    },
    { // sala 14
        { 1, { ENC_ARR_OR_0(s_r14_b0_p), 0, 0, 0, 0 } },
        { 1, { ENC_ARR_OR_0(s_r14_b1_p), 0, 0, ENC_ARR_OR_0(s_r14_b1_m) } },
        { 0 },
    },
    { // sala 15
        { 1, { ENC_ARR_OR_0(s_r15_b0_p), 0, 0, 0, 0 } },
        { 0 },
        { 0 },
    },
};
