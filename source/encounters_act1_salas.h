// Generado por tools/encuentros/gen_salas_rom.py desde tools/poster/salas/sala_NN.py. No editar a mano.
// Colocacion del poster por sala y bloque: piezas (ya en posicion legal del kit), rects de colision de sacos / alambre
// y miembros de cada grupo. Se incluye desde encounters_act1.c tras encounters_act1_tables.h.

typedef struct { uint8_t type, state; int16_t x, y; } RoomMember;     // ENC_E_*, ENC_S_*; x, y = pies, locales al bloque
typedef struct {
    const EncPieceDef *pieces; uint8_t n_pieces;
    const EncRectDef *rects; uint8_t n_rects;
    const RoomMember *members; uint8_t n_members;
} RoomLayout;

static const EncPieceDef s_r00_b0_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 0, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 216 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 344 },
};
static const RoomMember s_r00_b0_m[] = {
    { ENC_E_BEBE, ENC_S_AWAKE, 64, 160 },
    { ENC_E_BEBE, ENC_S_AWAKE, 96, 190 },
    { ENC_E_BEBE, ENC_S_AWAKE, 134, 168 },
    { ENC_E_BEBE, ENC_S_GUARD, 152, 214 },
    { ENC_E_BEBE, ENC_S_AWAKE, 80, 222 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 50 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 79 },
};
static const EncPieceDef s_r00_b1_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 0, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 216 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 344 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 344 },
};
static const RoomMember s_r00_b1_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 118, 110 },
    { ENC_E_BEBE, ENC_S_AWAKE, 62, 150 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 196 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 170 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 262 },
};
static const EncPieceDef s_r00_b2_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 0, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 216 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 216 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 344 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 344 },
};
static const RoomMember s_r00_b2_m[] = {
    { ENC_E_MONAGUILLO, ENC_S_AWAKE, 98, 100 },
    { ENC_E_MONAGUILLO, ENC_S_AWAKE, 112, 128 },
    { ENC_E_BEBE, ENC_S_AWAKE, 92, 160 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 184 },
    { ENC_E_BEBE, ENC_S_GUARD, 98, 208 },
    { ENC_E_BEBE, ENC_S_AWAKE, 114, 232 },
    { ENC_E_BEBE, ENC_S_AWAKE, 102, 262 },
};
static const EncPieceDef s_r01_b0_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 0, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 216 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 280 },
    { STRIP_PIECE_SACOS_B, 72, 328 },
};
static const EncRectDef s_r01_b0_r[] = {
    { ENC_R_SACOS, 72, 336, 64, 8 },
};
static const RoomMember s_r01_b0_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 150, 92 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 80, 140 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 130, 152 },
    { ENC_E_BEBE, ENC_S_AWAKE, 62, 186 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 208 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 200 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 50 },
};
static const EncPieceDef s_r01_b1_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 32 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 344 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 344 },
};
static const RoomMember s_r01_b1_m[] = {
    { ENC_E_CIRENEO, ENC_S_AWAKE, 104, 102 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 34 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 80, 150 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 132, 160 },
    { ENC_E_BEBE, ENC_S_AWAKE, 60, 192 },
    { ENC_E_BEBE, ENC_S_GUARD, 140, 198 },
    { ENC_E_BEBE, ENC_S_AWAKE, 172, 172 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 258 },
};
static const EncPieceDef s_r01_b2_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 32 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 216 },
    { STRIP_PIECE_BANCO_ROTO, 0, 256 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 280 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 344 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 344 },
};
static const RoomMember s_r01_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 34 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 78, 138 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 128, 146 },
    { ENC_E_BEBE, ENC_S_AWAKE, 50, 190 },
    { ENC_E_BEBE, ENC_S_AWAKE, 94, 204 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 192 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 52 },
};
static const EncPieceDef s_r02_b0_p[] = {
    { STRIP_PIECE_BANCO_ROTO, 0, 0 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 24 },
    { STRIP_PIECE_BANCO_ENTERO, 128, 280 },
    { STRIP_PIECE_SACOS_B, 72, 328 },
};
static const EncRectDef s_r02_b0_r[] = {
    { ENC_R_SACOS, 72, 336, 64, 8 },
};
static const RoomMember s_r02_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 79 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 34 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 70, 136 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 110, 128 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 146, 140 },
    { ENC_E_BEBE, ENC_S_AWAKE, 32, 176 },
    { ENC_E_BEBE, ENC_S_AWAKE, 90, 200 },
    { ENC_E_BEBE, ENC_S_GUARD, 132, 190 },
    { ENC_E_BEBE, ENC_S_AWAKE, 160, 215 },
};
static const EncPieceDef s_r02_b1_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 0, 24 },
    { STRIP_PIECE_BANCO_ROTO, 128, 24 },
    { STRIP_PIECE_SACOS, 128, 264 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 344 },
};
static const EncRectDef s_r02_b1_r[] = {
    { ENC_R_SACOS, 128, 284, 64, 4 },
};
static const RoomMember s_r02_b1_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 30, 104 },
    { ENC_E_OJO, ENC_S_GUARD, 178, 108 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 36 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 82, 150 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 130, 160 },
    { ENC_E_BEBE, ENC_S_AWAKE, 60, 200 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 206 },
    { ENC_E_BEBE, ENC_S_AWAKE, 118, 226 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 264 },
};
static const EncPieceDef s_r02_b2_p[] = {
    { STRIP_PIECE_BANCO_ENTERO, 0, 24 },
    { STRIP_PIECE_BANCO_ROTO, 128, 24 },
    { STRIP_PIECE_BANCO_ROTO, 128, 256 },
    { STRIP_PIECE_COLUMNA_ROTA, 0, 280 },
    { STRIP_PIECE_BANCO_ROTO, 128, 320 },
};
static const RoomMember s_r02_b2_m[] = {
    { ENC_E_CIRENEO, ENC_S_AWAKE, 58, 112 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 150, 122 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 34 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 92, 160 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 122, 172 },
    { ENC_E_BEBE, ENC_S_AWAKE, 70, 200 },
    { ENC_E_BEBE, ENC_S_GUARD, 160, 196 },
    { ENC_E_BEBE, ENC_S_AWAKE, 106, 266 },
};
static const EncPieceDef s_r03_b0_p[] = {
    { STRIP_PIECE_BANCO_ROTO, 0, 0 },
    { STRIP_PIECE_ALAMBRE, 104, 208 },
    { STRIP_PIECE_SACOS, 112, 344 },
};
static const EncRectDef s_r03_b0_r[] = {
    { ENC_R_ALAMBRE, 104, 216, 32, 16 },
    { ENC_R_SACOS, 112, 364, 64, 4 },
};
static const RoomMember s_r03_b0_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 104, 88 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 64 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 79 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 52, 150 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 90, 140 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 120, 150 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 152, 136 },
    { ENC_E_BEBE, ENC_S_AWAKE, 60, 204 },
    { ENC_E_BEBE, ENC_S_GUARD, 140, 202 },
    { ENC_E_BEBE, ENC_S_AWAKE, 170, 178 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 46 },
};
static const EncPieceDef s_r03_b1_p[] = {
    { STRIP_PIECE_BANCO_VOLCADO, 0, 0 },
    { STRIP_PIECE_BANCO_ROTO, 128, 24 },
    { STRIP_PIECE_SACOS, 72, 208 },
    { STRIP_PIECE_COLUMNA_ROTA, 0, 216 },
};
static const EncRectDef s_r03_b1_r[] = {
    { ENC_R_SACOS, 72, 228, 64, 4 },
};
static const RoomMember s_r03_b1_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 28, 122 },
    { ENC_E_OJO, ENC_S_GUARD, 180, 128 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 64 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 79 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 80, 150 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 110, 142 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 136, 156 },
    { ENC_E_BEBE, ENC_S_AWAKE, 50, 196 },
    { ENC_E_BEBE, ENC_S_GUARD, 130, 200 },
    { ENC_E_BEBE, ENC_S_AWAKE, 160, 212 },
    { ENC_E_BEBE, ENC_S_AWAKE, 170, 178 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 270 },
};
static const EncPieceDef s_r03_b2_p[] = {
    { STRIP_PIECE_BANCO_ROTO, 128, 24 },
    { STRIP_PIECE_BANCO_ROTO, 0, 64 },
    { STRIP_PIECE_BANCO_ENTERO, 0, 216 },
    { STRIP_PIECE_BANCO_VOLCADO, 0, 280 },
    { STRIP_PIECE_BANCO_ROTO, 0, 320 },
    { STRIP_PIECE_ALAMBRE, 104, 336 },
};
static const EncRectDef s_r03_b2_r[] = {
    { ENC_R_ALAMBRE, 104, 344, 32, 16 },
};
static const RoomMember s_r03_b2_m[] = {
    { ENC_E_OJO, ENC_S_GUARD, 182, 112 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 46, 34 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 150, 79 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 50, 132 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 156, 152 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 88, 168 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 118, 160 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 138, 188 },
    { ENC_E_BEBE, ENC_S_AWAKE, 60, 204 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 216 },
    { ENC_E_BEBE, ENC_S_GUARD, 150, 224 },
    { ENC_E_BEBE, ENC_S_DORMANT, 46, 61 },
};
static const EncPieceDef s_r04_b0_p[] = {
    { STRIP_PIECE_SACOS_B, 128, 0 },
    { STRIP_PIECE_CEPO, 16, 16 },
    { STRIP_PIECE_CEPO, 0, 208 },
    { STRIP_PIECE_SACOS, 128, 264 },
    { STRIP_PIECE_CEPO, 16, 272 },
    { STRIP_PIECE_CEPO, 0, 336 },
    { STRIP_PIECE_SACOS_B, 128, 336 },
};
static const EncRectDef s_r04_b0_r[] = {
    { ENC_R_SACOS, 128, 8, 64, 8 },
    { ENC_R_SACOS, 128, 284, 64, 4 },
    { ENC_R_SACOS, 128, 344, 64, 8 },
};
static const RoomMember s_r04_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 60, 84 },
    { ENC_E_BEBE, ENC_S_AWAKE, 40, 140 },
    { ENC_E_BEBE, ENC_S_GUARD, 56, 154 },
    { ENC_E_BEBE, ENC_S_AWAKE, 36, 166 },
    { ENC_E_BEBE, ENC_S_AWAKE, 98, 122 },
    { ENC_E_BEBE, ENC_S_AWAKE, 124, 144 },
    { ENC_E_BEBE, ENC_S_GUARD, 152, 126 },
};
static const EncPieceDef s_r05_b0_p[] = {
    { STRIP_PIECE_CAPULLO, 24, 0 },
    { STRIP_PIECE_CAPULLO, 24, 256 },
    { STRIP_PIECE_CEPO, 144, 280 },
    { STRIP_PIECE_SACOS_B, 72, 328 },
    { STRIP_PIECE_SACOS_REMATE, 120, 352 },
};
static const EncRectDef s_r05_b0_r[] = {
    { ENC_R_SACOS, 72, 336, 64, 8 },
    { ENC_R_SACOS, 120, 364, 64, 4 },
};
static const RoomMember s_r05_b0_m[] = {
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 150, 98 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 150, 140 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 138 },
    { ENC_E_BEBE, ENC_S_AWAKE, 96, 162 },
    { ENC_E_BEBE, ENC_S_GUARD, 128, 170 },
    { ENC_E_BEBE, ENC_S_AWAKE, 160, 178 },
    { ENC_E_BEBE, ENC_S_AWAKE, 122, 112 },
};
static const EncPieceDef s_r06_b0_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 152 },
};
static const RoomMember s_r06_b0_m[] = {
    { ENC_E_BEBE, ENC_S_AWAKE, 150, 142 },
    { ENC_E_BEBE, ENC_S_GUARD, 164, 154 },
    { ENC_E_BEBE, ENC_S_AWAKE, 144, 158 },
    { ENC_E_BEBE, ENC_S_AWAKE, 157, 168 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 112 },
    { ENC_E_BEBE, ENC_S_AWAKE, 98, 130 },
    { ENC_E_BEBE, ENC_S_GUARD, 70, 140 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 96, 16 },
};
static const EncPieceDef s_r06_b1_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 152 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 152 },
};
static const RoomMember s_r06_b1_m[] = {
    { ENC_E_MONAGUILLO, ENC_S_AWAKE, 70, 150 },
    { ENC_E_MONAGUILLO, ENC_S_AWAKE, 125, 262 },
    { ENC_E_BEBE, ENC_S_DORMANT, 35, 108 },
    { ENC_E_BEBE, ENC_S_DORMANT, 155, 108 },
    { ENC_E_BEBE, ENC_S_AWAKE, 62, 198 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 214 },
    { ENC_E_BEBE, ENC_S_AWAKE, 88, 246 },
};
static const EncPieceDef s_r06_b2_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 152 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 152 },
};
static const RoomMember s_r06_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 118, 122 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 94, 110 },
    { ENC_E_BEBE, ENC_S_AWAKE, 74, 176 },
    { ENC_E_BEBE, ENC_S_AWAKE, 100, 198 },
    { ENC_E_BEBE, ENC_S_GUARD, 118, 160 },
    { ENC_E_BEBE, ENC_S_AWAKE, 86, 142 },
};
static const EncPieceDef s_r07_b0_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 152 },
};
static const RoomMember s_r07_b0_m[] = {
    { ENC_E_OJO, ENC_S_AWAKE, 98, 66 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 64, 104 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 122, 98 },
    { ENC_E_BEBE, ENC_S_AWAKE, 90, 140 },
    { ENC_E_BEBE, ENC_S_AWAKE, 116, 153 },
    { ENC_E_BEBE, ENC_S_GUARD, 76, 126 },
    { ENC_E_BEBE, ENC_S_AWAKE, 124, 144 },
};
static const EncPieceDef s_r07_b1_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 152 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 152 },
};
static const RoomMember s_r07_b1_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 96, 52 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 68, 92 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 126, 84 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 112, 232 },
    { ENC_E_BEBE, ENC_S_AWAKE, 70, 205 },
    { ENC_E_BEBE, ENC_S_AWAKE, 96, 188 },
    { ENC_E_BEBE, ENC_S_AWAKE, 84, 228 },
    { ENC_E_BEBE, ENC_S_GUARD, 100, 160 },
};
static const EncPieceDef s_r07_b2_p[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 24 },
    { STRIP_PIECE_COLUMNA_ENTERA, 0, 152 },
    { STRIP_PIECE_COLUMNA_ENTERA, 128, 152 },
};
static const RoomMember s_r07_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 60, 58 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 62, 104 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 70, 150 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 122, 146 },
    { ENC_E_BEBE, ENC_S_DORMANT, 150, 106 },
    { ENC_E_BEBE, ENC_S_DORMANT, 160, 111 },
    { ENC_E_BEBE, ENC_S_AWAKE, 82, 192 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 208 },
};
static const EncPieceDef s_r08_b0_p[] = {
    { STRIP_PIECE_CATRE, 16, 16 },
    { STRIP_PIECE_CATRE, 144, 16 },
    { STRIP_PIECE_CATRE, 16, 216 },
    { STRIP_PIECE_CATRE, 16, 272 },
    { STRIP_PIECE_CATRE, 144, 272 },
    { STRIP_PIECE_BIOMBO, 0, 328 },
    { STRIP_PIECE_CATRE, 144, 344 },
};
static const RoomMember s_r08_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 34, 82 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 84, 74 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 26, 128 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 76, 132 },
    { ENC_E_BEBE, ENC_S_GUARD, 152, 96 },
    { ENC_E_BEBE, ENC_S_AWAKE, 178, 128 },
    { ENC_E_BEBE, ENC_S_AWAKE, 118, 178 },
    { ENC_E_BEBE, ENC_S_GUARD, 58, 196 },
};
static const EncPieceDef s_r08_b1_p[] = {
    { STRIP_PIECE_CATRE, 16, 16 },
    { STRIP_PIECE_CATRE, 144, 16 },
    { STRIP_PIECE_CATRE, 16, 216 },
    { STRIP_PIECE_CATRE, 144, 216 },
    { STRIP_PIECE_CATRE, 16, 272 },
    { STRIP_PIECE_CATRE, 144, 272 },
    { STRIP_PIECE_BIOMBO, 128, 328 },
    { STRIP_PIECE_CATRE, 16, 344 },
};
static const RoomMember s_r08_b1_m[] = {
    { ENC_E_OJO, ENC_S_AWAKE, 100, 80 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 60, 128 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 142, 122 },
    { ENC_E_BEBE, ENC_S_AWAKE, 50, 176 },
    { ENC_E_BEBE, ENC_S_GUARD, 112, 190 },
    { ENC_E_BEBE, ENC_S_AWAKE, 150, 168 },
    { ENC_E_BEBE, ENC_S_DORMANT, 162, 355 },
};
static const EncPieceDef s_r08_b2_p[] = {
    { STRIP_PIECE_CATRE, 16, 16 },
    { STRIP_PIECE_CATRE, 144, 16 },
    { STRIP_PIECE_CATRE, 144, 216 },
    { STRIP_PIECE_CATRE, 16, 272 },
    { STRIP_PIECE_CATRE, 144, 272 },
};
static const RoomMember s_r08_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 160, 82 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 138, 112 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 182, 120 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 72, 158 },
    { ENC_E_BEBE, ENC_S_GUARD, 60, 100 },
    { ENC_E_BEBE, ENC_S_AWAKE, 100, 130 },
    { ENC_E_BEBE, ENC_S_GUARD, 124, 194 },
    { ENC_E_BEBE, ENC_S_AWAKE, 152, 204 },
};
static const EncPieceDef s_r09_b0_p[] = {
    { STRIP_PIECE_OSARIO_LADO, 16, 0 },
    { STRIP_PIECE_OSARIO_LADO, 144, 0 },
    { STRIP_PIECE_OSARIO_LADO, 8, 208 },
    { STRIP_PIECE_OSARIO_LADO, 16, 256 },
    { STRIP_PIECE_OSARIO_LADO, 144, 256 },
    { STRIP_PIECE_OSARIO_LADO, 16, 304 },
    { STRIP_PIECE_OSARIO_LADO, 144, 304 },
    { STRIP_PIECE_CALAVERAS_PILA, 152, 352 },
};
static const RoomMember s_r09_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 28, 70 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 66, 62 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 102, 72 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 34, 120 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 80, 126 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 126, 118 },
    { ENC_E_BEBE, ENC_S_DORMANT, 180, 113 },
    { ENC_E_BEBE, ENC_S_DORMANT, 195, 116 },
    { ENC_E_BEBE, ENC_S_AWAKE, 100, 168 },
    { ENC_E_BEBE, ENC_S_GUARD, 52, 178 },
};
static const EncPieceDef s_r09_b1_p[] = {
    { STRIP_PIECE_OSARIO_LADO, 16, 0 },
    { STRIP_PIECE_OSARIO_LADO, 144, 0 },
    { STRIP_PIECE_OSARIO_LADO, 144, 176 },
    { STRIP_PIECE_OSARIO_LADO, 16, 256 },
    { STRIP_PIECE_OSARIO_LADO, 144, 256 },
    { STRIP_PIECE_OSARIO_LADO, 16, 304 },
    { STRIP_PIECE_OSARIO_LADO, 144, 304 },
};
static const RoomMember s_r09_b1_m[] = {
    { ENC_E_OJO, ENC_S_AWAKE, 30, 76 },
    { ENC_E_OJO, ENC_S_AWAKE, 180, 150 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 98, 66 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 72, 118 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 134, 104 },
    { ENC_E_BEBE, ENC_S_DORMANT, 27, 118 },
    { ENC_E_BEBE, ENC_S_GUARD, 138, 182 },
    { ENC_E_BEBE, ENC_S_AWAKE, 62, 172 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 160 },
};
static const EncPieceDef s_r09_b2_p[] = {
    { STRIP_PIECE_OSARIO_ESTANTE, 0, 0 },
    { STRIP_PIECE_OSARIO_ESTANTE, 160, 0 },
    { STRIP_PIECE_OSARIO_LADO, 144, 176 },
    { STRIP_PIECE_OSARIO_LADO, 8, 208 },
    { STRIP_PIECE_OSARIO_LADO, 16, 256 },
    { STRIP_PIECE_OSARIO_LADO, 144, 256 },
    { STRIP_PIECE_OSARIO_LADO, 16, 304 },
    { STRIP_PIECE_OSARIO_LADO, 144, 304 },
};
static const RoomMember s_r09_b2_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 28, 90 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 52, 122 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 160, 112 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 68, 164 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 142, 176 },
    { ENC_E_BEBE, ENC_S_GUARD, 100, 130 },
    { ENC_E_BEBE, ENC_S_AWAKE, 120, 152 },
    { ENC_E_BEBE, ENC_S_AWAKE, 178, 150 },
};
static const EncPieceDef s_r10_b0_p[] = {
    { STRIP_PIECE_CANDELABRO_PIE, 48, 8 },
    { STRIP_PIECE_RECLINATORIO, 16, 248 },
    { STRIP_PIECE_RECLINATORIO, 144, 248 },
    { STRIP_PIECE_RECLINATORIO, 16, 288 },
    { STRIP_PIECE_RECLINATORIO, 144, 288 },
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
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 58, 164 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 94, 172 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 128, 162 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 162, 170 },
};
static const EncPieceDef s_r11_b0_p[] = {
    { STRIP_PIECE_RECLINATORIO, 16, 32 },
    { STRIP_PIECE_RECLINATORIO, 144, 32 },
    { STRIP_PIECE_RECLINATORIO, 16, 72 },
    { STRIP_PIECE_RECLINATORIO, 144, 72 },
    { STRIP_PIECE_RECLINATORIO, 16, 120 },
    { STRIP_PIECE_RECLINATORIO, 144, 120 },
    { STRIP_PIECE_RECLINATORIO, 16, 160 },
    { STRIP_PIECE_RECLINATORIO, 144, 160 },
    { STRIP_PIECE_RECLINATORIO, 16, 248 },
    { STRIP_PIECE_RECLINATORIO, 16, 288 },
    { STRIP_PIECE_RECLINATORIO, 144, 288 },
    { STRIP_PIECE_RECLINATORIO, 16, 328 },
    { STRIP_PIECE_RECLINATORIO, 144, 328 },
};
static const EncPieceDef s_r11_b1_p[] = {
    { STRIP_PIECE_CANDELABRO_PIE, 48, 8 },
    { STRIP_PIECE_RECLINATORIO, 16, 248 },
    { STRIP_PIECE_RECLINATORIO, 144, 248 },
};
static const RoomMember s_r11_b1_m[] = {
    { ENC_E_PARROCO, ENC_S_GUARD, 90, 66 },
    { ENC_E_PARROCO, ENC_S_GUARD, 131, 62 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 76, 124 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 142, 164 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 106, 204 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 29, 301 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 178, 304 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 36, 366 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 170, 364 },
    { ENC_E_MONJA, ENC_S_DORMANT, 26, 47 },
    { ENC_E_MONJA, ENC_S_DORMANT, 171, 46 },
};
static const EncPieceDef s_r12_b0_p[] = {
    { STRIP_PIECE_CAPULLO, 24, 0 },
    { STRIP_PIECE_CAPULLO, 152, 0 },
    { STRIP_PIECE_CEPO, 16, 280 },
    { STRIP_PIECE_CEPO, 144, 280 },
    { STRIP_PIECE_ALAMBRE, 16, 336 },
    { STRIP_PIECE_ALAMBRE, 144, 336 },
};
static const EncRectDef s_r12_b0_r[] = {
    { ENC_R_ALAMBRE, 16, 344, 32, 16 },
    { ENC_R_ALAMBRE, 144, 344, 32, 16 },
};
static const RoomMember s_r12_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 40 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 84, 80 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 128, 76 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 140, 222 },
    { ENC_E_CIRENEO, ENC_S_AWAKE, 100, 148 },
    { ENC_E_BEBE, ENC_S_AWAKE, 70, 118 },
    { ENC_E_BEBE, ENC_S_AWAKE, 118, 106 },
    { ENC_E_BEBE, ENC_S_GUARD, 90, 170 },
};
static const EncPieceDef s_r12_b1_p[] = {
    { STRIP_PIECE_CEPO, 16, 16 },
    { STRIP_PIECE_CEPO, 144, 16 },
    { STRIP_PIECE_CAPULLO, 40, 304 },
    { STRIP_PIECE_CAPULLO, 168, 304 },
};
static const RoomMember s_r12_b1_m[] = {
    { ENC_E_OJO, ENC_S_AWAKE, 30, 88 },
    { ENC_E_OJO, ENC_S_AWAKE, 178, 92 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 104, 30 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 68, 76 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 146, 70 },
    { ENC_E_BEBE, ENC_S_AWAKE, 80, 170 },
    { ENC_E_BEBE, ENC_S_AWAKE, 112, 150 },
    { ENC_E_BEBE, ENC_S_GUARD, 142, 186 },
    { ENC_E_BEBE, ENC_S_AWAKE, 70, 216 },
};
static const EncPieceDef s_r13_b0_p[] = {
    { STRIP_PIECE_RELICARIO, 0, 0 },
    { STRIP_PIECE_RECLINATORIO, 144, 248 },
    { STRIP_PIECE_RECLINATORIO, 48, 272 },
    { STRIP_PIECE_RECLINATORIO, 144, 288 },
};
static const RoomMember s_r13_b0_m[] = {
    { ENC_E_EXVOTO, ENC_S_PRAY, 82, 168 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 128, 161 },
    { ENC_E_OJO, ENC_S_AWAKE, 26, 174 },
    { ENC_E_OJO, ENC_S_AWAKE, 184, 178 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 64, 198 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 103, 204 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 142, 196 },
    { ENC_E_BEBE, ENC_S_AWAKE, 48, 228 },
    { ENC_E_BEBE, ENC_S_AWAKE, 86, 236 },
    { ENC_E_BEBE, ENC_S_AWAKE, 120, 224 },
    { ENC_E_BEBE, ENC_S_GUARD, 155, 240 },
    { ENC_E_BEBE, ENC_S_AWAKE, 104, 246 },
};
static const EncPieceDef s_r14_b0_p[] = {
    { STRIP_PIECE_SANTO, 0, 0 },
    { STRIP_PIECE_SANTO_DER, 144, 0 },
    { STRIP_PIECE_SANTO_DER, 144, 128 },
    { STRIP_PIECE_SANTO_DER, 144, 256 },
    { STRIP_PIECE_SANTO, 0, 312 },
};
static const EncPieceDef s_r14_b1_p[] = {
    { STRIP_PIECE_CAPULLO, 24, 0 },
    { STRIP_PIECE_SANTO_DER, 144, 0 },
    { STRIP_PIECE_SANTO, 0, 256 },
    { STRIP_PIECE_SANTO_DER, 144, 256 },
};
static const RoomMember s_r14_b1_m[] = {
    { ENC_E_MONJA, ENC_S_DORMANT, 95, 44 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 38, 112 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 99, 108 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 158, 118 },
    { ENC_E_EXVOTO, ENC_S_PRAY, 66, 142 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 30, 178 },
    { ENC_E_MONAGUILLO, ENC_S_GUARD, 152, 182 },
    { ENC_E_MONAGUILLO, ENC_S_DORMANT, 71, 285 },
    { ENC_E_MONAGUILLO, ENC_S_DORMANT, 137, 288 },
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
        { 1, { ENC_ARR_OR_0(s_r12_b1_p), 0, 0, ENC_ARR_OR_0(s_r12_b1_m) } },
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
        { 0 },
        { 0 },
        { 0 },
    },
};
