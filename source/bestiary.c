#include "bestiary.h"
#include "bestiary_font.h"
#include "bestiary_exvoto.h"
#include "player_sprite.h"
#include <nds.h>
#include <string.h>
#include <stdio.h>

#define BESTIARY_SCREEN_W 256
#define BESTIARY_SCREEN_H 192

#define COLOR_BLACK_OPAQUE (0x8000)
#define COLOR_BORDER       (RGB15(8, 8, 8) | 0x8000)
#define COLOR_SEPARATOR    (RGB15(6, 6, 6) | 0x8000)
#define COLOR_IVORY        (RGB15(29, 28, 26) | 0x8000)
#define COLOR_BEHAVIOR     (RGB15(26, 26, 24) | 0x8000)
#define COLOR_WARM_GRAY    (RGB15(20, 19, 18) | 0x8000)
#define COLOR_QUOTE        (RGB15(24, 23, 21) | 0x8000)
#define COLOR_BUTTON       (RGB15(22, 21, 20) | 0x8000)
#define COLOR_HINT         (RGB15(12, 12, 12) | 0x8000)

volatile BestiaryDebugState g_bestiary_debug = {0, 0, 0, 0};

typedef struct {
    const char *id;
    const char *name;
    const char *behavior;
    const char *lore;
    const char *quote;
    uint8_t vida, veloc, amenaza; /* 1-5; 0 = sin bloque de datos (el heroe) */
    const char *hace;
    const char *truco;
} BestiaryEntry;

#define BESTIARY_NUM_ENTRIES 5

static const BestiaryEntry s_entries[BESTIARY_NUM_ENTRIES] = {
    {
        .id = "corazon",
        .name = "El Corazón Abierto",
        .behavior = "Carga su fe en cruz y desata un haz que atraviesa filas.",
        .lore = "Último capellán de la columna. Pidió un arma cuando faltó la pólvora y Dios le abrió el pecho; cada milagro le consume un poco más, pero la fe no le deja morir.",
        .quote = "«No es mi corazón. Solo lo llevo.»"
    },
    {
        .id = "exvoto",
        .name = "El Exvoto",
        .behavior = "Avanza en masa sin descanso; cae al primer impacto.",
        .vida = 1, .veloc = 1, .amenaza = 1,
        .hace = "Te sigue sin parar y, si lo apuntas con el rayo cargado, se aparta a un lado.",
        .truco = "Dispara justo tras su esquiva: tarda en repetirla.",
        .lore = "Fieles que rezaron hasta volverse figuras de cera. Siguen en procesión con las manos en rezo; la cera no resiste la luz.",
        .quote = "«Pidieron no estar solos. Les fue concedido.»"
    },
    {
        .id = "cireneo",
        .name = "El Cireneo",
        .behavior = "Se agacha antes de embestir en línea recta; no puede girar.",
        .vida = 3, .veloc = 5, .amenaza = 3,
        .hace = "Se agacha y embiste en línea recta; no gira durante la embestida.",
        .truco = "Dispárale al recuperarse.",
        .lore = "Desertó y pidió que le clavaran la cruz a la espalda para no volver a huir. Si choca contra una columna, queda crucificado contra la piedra.",
        .quote = "«Ayudó a cargar una cruz. Ahora la cruz le carga a él.»"
    },
    {
        .id = "ojo",
        .name = "El Ojo del Tribunal",
        .behavior = "Vigila con su farol, fija la línea de juicio y sentencia desde la boca.",
        .vida = 2, .veloc = 1, .amenaza = 3,
        .hace = "Se para a distancia, te marca con una banda verde y dispara por la línea fijada.",
        .truco = "La línea se congela antes de disparar: muévete.",
        .lore = "Inquisidores que cambiaron sus ojos por una linterna del juicio. Su mirada verde te examina; cuando se queda quieta, ya ha dictado sentencia.",
        .quote = "«La linterna no ve culpables. Los fabrica.»"
    },
    {
        .id = "abanderado",
        .name = "El Abanderado",
        .behavior = "Patrulla con el asta; al divisarte te apunta e invoca exvotos de jóvenes suplicantes.",
        .vida = 5, .veloc = 1, .amenaza = 5,
        .hace = "Al verte, invoca monaguillos lentos.",
        .truco = "Úsale las columnas; limpia monaguillos.",
        .lore = "Juró que el estandarte jamás tocaría el suelo. Apoyado en él vaga reuniendo a los caídos; de los charcos que señala brotan exvotos de jóvenes suplicantes que aún marchan tras su bandera.",
        .quote = "«Mientras el asta siga en pie, nadie se retira.»"
    }
};

/* Binary portrait structs matching tools/gen_bestiary_portraits.py */
typedef struct {
    uint16_t magic;          /* 0x4251 */
    uint8_t  num_dirs;       /* 8 */
    uint8_t  num_frames;
    uint8_t  canvas_w;       /* 160 */
    uint8_t  canvas_h;       /* 160 */
    uint8_t  pad[2];
    uint16_t palette[256];   /* 512 bytes */
    uint32_t dir_offsets[8];
    uint32_t dir_sizes[8];
} __attribute__((packed)) BestiaryPortraitFileHeader;

typedef struct {
    uint8_t u_min_x;
    uint8_t u_min_y;
    uint8_t u_max_x;
    uint8_t u_max_y;
} __attribute__((packed)) BestiaryDirHeader;

typedef struct {
    uint8_t  bx;
    uint8_t  by;
    uint8_t  bw;
    uint8_t  bh;
    uint32_t offset;
} __attribute__((packed)) BestiaryPortraitFrame;

/* Static direction buffer: 160 KB is enough for the largest single direction (Cireneo ~145.2 KB) */
#define BESTIARY_PORTRAIT_BUF_SIZE (160 * 1024)
static uint8_t s_portrait_buf[BESTIARY_PORTRAIT_BUF_SIZE];
static BestiaryPortraitFileHeader s_portrait_hdr;
static int s_portrait_loaded_entry = -1;
static int s_portrait_loaded_dir = -1;
static int s_portrait_valid = 0;

static const char *s_dir_names[8] = { "S", "SO", "O", "NO", "N", "NE", "E", "SE" };

static void draw_border_rect(uint16_t *fb, uint16_t color) {
    if (!fb) return;
    uint16_t *top_row = fb + (4 << 8);
    uint16_t *bot_row = fb + (187 << 8);
    for (int x = 4; x <= 251; x++) {
        top_row[x] = color;
        bot_row[x] = color;
    }
    for (int y = 4; y <= 187; y++) {
        uint16_t *row = fb + (y << 8);
        row[4] = color;
        row[251] = color;
    }
}

static int load_portrait_direction(int entry_idx, int dir) {
    if (entry_idx < 0 || entry_idx >= BESTIARY_NUM_ENTRIES) return 0;
    dir &= 7;

    char path[64];
    snprintf(path, sizeof(path), "nitro:/bestiary/%s.bin", s_entries[entry_idx].id);

    FILE *f = fopen(path, "rb");
    if (!f) {
        s_portrait_valid = 0;
        return 0;
    }

    if (entry_idx != s_portrait_loaded_entry) {
        if (fread(&s_portrait_hdr, sizeof(s_portrait_hdr), 1, f) != 1 || s_portrait_hdr.magic != 0x4251) {
            fclose(f);
            s_portrait_valid = 0;
            return 0;
        }
        s_portrait_loaded_entry = entry_idx;
    }

    uint32_t d_offset = s_portrait_hdr.dir_offsets[dir];
    uint32_t d_size = s_portrait_hdr.dir_sizes[dir];
    if (d_size > BESTIARY_PORTRAIT_BUF_SIZE) {
        fclose(f);
        s_portrait_valid = 0;
        return 0;
    }

    if (fseek(f, (long)d_offset, SEEK_SET) != 0) {
        fclose(f);
        s_portrait_valid = 0;
        return 0;
    }

    if (fread(s_portrait_buf, 1, d_size, f) != d_size) {
        fclose(f);
        s_portrait_valid = 0;
        return 0;
    }

    fclose(f);
    s_portrait_loaded_dir = dir;
    s_portrait_valid = 1;
    return 1;
}

static void draw_portrait_frame_160(uint16_t *fb, int frame_idx) {
    if (!fb || !s_portrait_valid) return;
    if (frame_idx < 0 || frame_idx >= s_portrait_hdr.num_frames) return;

    const BestiaryDirHeader *dh = (const BestiaryDirHeader *)s_portrait_buf;
    const BestiaryPortraitFrame *frames = (const BestiaryPortraitFrame *)(s_portrait_buf + sizeof(BestiaryDirHeader));
    const uint8_t *pixel_pool = s_portrait_buf + sizeof(BestiaryDirHeader) + sizeof(BestiaryPortraitFrame) * s_portrait_hdr.num_frames;

    /* Center within screen frame [4..251, 4..187] using bounding box union */
    int u_cx = (dh->u_min_x + dh->u_max_x) >> 1;
    int u_cy = (dh->u_min_y + dh->u_max_y) >> 1;
    int canvas_x = 128 - u_cx;
    int canvas_y = 96 - u_cy;

    const BestiaryPortraitFrame *fr = &frames[frame_idx];
    if (fr->bw == 0 || fr->bh == 0) return;

    int dst_x = canvas_x + fr->bx;
    int dst_y = canvas_y + fr->by;
    const uint8_t *src_pixels = pixel_pool + fr->offset;

    for (int y = 0; y < fr->bh; y++) {
        int py = dst_y + y;
        if (py < 4 || py > 187) continue;
        uint16_t *fb_row = fb + (py << 8);
        const uint8_t *prow = src_pixels + y * fr->bw;
        for (int x = 0; x < fr->bw; x++) {
            uint8_t idx = prow[x];
            if (idx != 0) {
                int px = dst_x + x;
                if (px >= 4 && px <= 251) {
                    fb_row[px] = s_portrait_hdr.palette[idx];
                }
            }
        }
    }
}

/* Fallback 2x nearest-neighbor drawer for original ROM sprites if NitroFS file is missing */
static void draw_sprite_2x(uint16_t *fb, int canvas_w, int canvas_h,
                           const uint8_t *bounds, const uint16_t *src) {
    if (!fb || !bounds || !src) return;
    int min_x = bounds[0], min_y = bounds[1], bw = bounds[2], bh = bounds[3];
    if (bw <= 0 || bh <= 0) return;
    int pitch = (bw + 1) & ~1;
    int dst_x = (BESTIARY_SCREEN_W - (canvas_w << 1)) >> 1;
    int dst_y = (BESTIARY_SCREEN_H - (canvas_h << 1)) >> 1;

    for (int y = 0; y < bh; y++) {
        int py0 = dst_y + ((min_y + y) << 1);
        int py1 = py0 + 1;
        const uint16_t *srow = src + y * pitch;
        for (int x = 0; x < bw; x++) {
            uint16_t px = srow[x];
            if (px & 0x8000) {
                int px0 = dst_x + ((min_x + x) << 1);
                int px1 = px0 + 1;
                uint16_t col = (uint16_t)(px | 0x8000);
                if (py0 >= 0 && py0 < BESTIARY_SCREEN_H) {
                    uint16_t *row0 = fb + (py0 << 8);
                    if (px0 >= 0 && px0 < BESTIARY_SCREEN_W) row0[px0] = col;
                    if (px1 >= 0 && px1 < BESTIARY_SCREEN_W) row0[px1] = col;
                }
                if (py1 >= 0 && py1 < BESTIARY_SCREEN_H) {
                    uint16_t *row1 = fb + (py1 << 8);
                    if (px0 >= 0 && px0 < BESTIARY_SCREEN_W) row1[px0] = col;
                    if (px1 >= 0 && px1 < BESTIARY_SCREEN_W) row1[px1] = col;
                }
            }
        }
    }
}

static void draw_fallback_sprite_2x(uint16_t *fb, int entry_idx, uint32_t anim_tick) {
    if (entry_idx == 0) {
        uint32_t t = anim_tick % 104;
        int frame = (t < 32) ? (7 - (int)(t >> 2)) : ((t < 56) ? 0 : ((t < 88) ? (int)((t - 56) >> 2) : 7));
        const uint8_t *bounds = g_player_shot_frame_bounds[0][frame];
        const uint16_t *src = &g_player_shot_frames[g_player_shot_frame_offsets[0][frame]];
        draw_sprite_2x(fb, HERO_SHOT_SPRITE_W, HERO_SHOT_SPRITE_H, bounds, src);
    } else if (entry_idx == 1) {
        int frame = (int)((anim_tick >> 2) % BESTIARY_EXVOTO_NUM_FRAMES);
        const uint8_t *bounds = bestiary_exvoto_bounds[frame];
        const uint16_t *src = &bestiary_exvoto_frames[bestiary_exvoto_offsets[frame]];
        draw_sprite_2x(fb, BESTIARY_EXVOTO_FRAME_W, BESTIARY_EXVOTO_FRAME_H, bounds, src);
    } else if (entry_idx == 2) {
        uint32_t t = anim_tick % 100;
        if (t < 24) {
            const uint8_t *bounds = g_charger_telegraph_frame_bounds[0][0];
            const uint16_t *src = &g_charger_telegraph_frames[g_charger_telegraph_frame_offsets[0][0]];
            draw_sprite_2x(fb, CHARGER_SPRITE_W, CHARGER_SPRITE_H, bounds, src);
        } else if (t < 60) {
            int cf = (int)(((t - 24) / 3) % CHARGER_CHARGE_NUM_FRAMES);
            const uint8_t *bounds = g_charger_charge_frame_bounds[0][cf];
            const uint16_t *src = &g_charger_charge_frames[g_charger_charge_frame_offsets[0][cf]];
            draw_sprite_2x(fb, CHARGER_SPRITE_W, CHARGER_SPRITE_H, bounds, src);
        } else {
            int mf = (int)(((t - 60) / 5) % 4);
            const uint8_t *bounds = g_charger_frame_bounds[0][mf];
            const uint16_t *src = &g_charger_frames[g_charger_frame_offsets[0][mf]];
            draw_sprite_2x(fb, CHARGER_SPRITE_W, CHARGER_SPRITE_H, bounds, src);
        }
    } else if (entry_idx == 3) {
        uint32_t t = anim_tick % 96;
        if (t < 48) {
            int lf = (int)((t / 6) % OJO_LOOK_NUM_FRAMES);
            const uint8_t *bounds = g_ojo_look_frame_bounds[0][lf];
            const uint16_t *src = &g_ojo_look_frames[g_ojo_look_frame_offsets[0][lf]];
            draw_sprite_2x(fb, PLAYER_SPRITE_W, PLAYER_SPRITE_H, bounds, src);
        } else {
            int sf = (int)((t - 48) / 5);
            if (sf > 5) sf = 5;
            const uint8_t *bounds = g_ojo_sentence_frame_bounds[0][sf];
            const uint16_t *src = &g_ojo_sentence_frames[g_ojo_sentence_frame_offsets[0][sf]];
            draw_sprite_2x(fb, PLAYER_SPRITE_W, PLAYER_SPRITE_H, bounds, src);
        }
    } else if (entry_idx == 4) {
        int frame = (int)((anim_tick / 7) % 8);
        const uint8_t *bounds = g_character_frame_bounds[CHAR_ABANDERADO][0][frame];
        const uint16_t *src = &g_character_frames[CHAR_ABANDERADO][g_character_frame_offsets[CHAR_ABANDERADO][0][frame]];
        draw_sprite_2x(fb, 60, 60, bounds, src);
    }
}

static int count_wrapped_lines(const char *utf8, int max_w) {
    if (!utf8 || max_w <= 0) return 0;
    int lines = 1;
    int cur_x = 0;
    const char *p = utf8;
    while (*p) {
        if (*p == '\n') {
            lines++;
            cur_x = 0;
            p++;
            continue;
        }
        if (*p == '\r') {
            p++;
            continue;
        }
        if (*p == ' ') {
            if (cur_x == 0) {
                p++;
                continue;
            }
            const BestiaryGlyph *g_sp = bestiary_font_get_glyph(' ');
            int sp_w = g_sp ? (int)g_sp->advance : 3;
            cur_x += sp_w;
            p++;
            continue;
        }

        const char *w_ptr = p;
        int word_w = 0;
        while (*w_ptr && *w_ptr != ' ' && *w_ptr != '\n' && *w_ptr != '\r') {
            uint32_t cp = 0;
            uint8_t c = (uint8_t)*w_ptr;
            if (c < 0x80) {
                cp = c;
                w_ptr++;
            } else if ((c & 0xE0) == 0xC0) {
                cp = ((c & 0x1F) << 6) | (w_ptr[1] & 0x3F);
                w_ptr += 2;
            } else if ((c & 0xF0) == 0xE0) {
                cp = ((c & 0x0F) << 12) | ((w_ptr[1] & 0x3F) << 6) | (w_ptr[2] & 0x3F);
                w_ptr += 3;
            } else {
                w_ptr++;
                continue;
            }
            const BestiaryGlyph *g = bestiary_font_get_glyph(cp);
            if (!g) g = bestiary_font_get_glyph('?');
            if (g) word_w += g->advance;
        }

        if (cur_x + word_w > max_w && cur_x > 0) {
            lines++;
            cur_x = 0;
        }
        cur_x += word_w;
        p = w_ptr;
    }
    return lines;
}

static void draw_scale_mark(uint16_t *fb, int x, int y, int filled) {
    uint16_t on = COLOR_IVORY;
    for (int j = 0; j < 5; j++) {
        for (int i = 0; i < 3; i++) {
            int edge = (i == 0 || i == 2 || j == 0 || j == 4);
            if (filled) fb[((y + j) << 8) + x + i] = on;
            else if (edge) fb[((y + j) << 8) + x + i] = COLOR_WARM_GRAY;
        }
    }
}

static void draw_bottom_card(uint16_t *fb, int entry_idx) {
    if (!fb || entry_idx < 0 || entry_idx >= BESTIARY_NUM_ENTRIES) return;
    uint32_t black_pair = 0x80008000;
    swiFastCopy(&black_pair, fb, COPY_MODE_FILL | (BESTIARY_SCREEN_W * BESTIARY_SCREEN_H * 2 / 4));
    draw_border_rect(fb, COLOR_BORDER);

    const BestiaryEntry *e = &s_entries[entry_idx];

    /* Header: Name, Page indicator */
    bestiary_font_draw_utf8(fb, 12, 10, e->name, COLOR_IVORY);

    char pbuf[8];
    snprintf(pbuf, sizeof(pbuf), "%d/%d", entry_idx + 1, BESTIARY_NUM_ENTRIES);
    int pw = bestiary_font_measure_utf8(pbuf);
    bestiary_font_draw_utf8(fb, 244 - pw, 10, pbuf, COLOR_WARM_GRAY);

    /* Separator line under header */
    uint16_t *sep_row = fb + (24 << 8);
    for (int x = 12; x <= 243; x++) sep_row[x] = COLOR_SEPARATOR;

    int cur_y = 28;
    if (e->vida) {
        /* Fila de escalas: etiqueta + 5 marcas (llenas / vacias) */
        static const char *const labels[3] = { "VIDA", "VELOC.", "AMENAZA" };
        const int vals[3] = { e->vida, e->veloc, e->amenaza };
        int x = 12;
        for (int i = 0; i < 3; i++) {
            bestiary_font_draw_utf8(fb, x, cur_y, labels[i], COLOR_WARM_GRAY);
            x += bestiary_font_measure_utf8(labels[i]) + 3;
            for (int m = 0; m < 5; m++) {
                draw_scale_mark(fb, x, cur_y + 3, m < vals[i]);
                x += 5;
            }
            x += 5;
        }
        cur_y += 13;
        char buf[160];
        snprintf(buf, sizeof(buf), "HACE: %s", e->hace);
        bestiary_font_draw_wrapped(fb, 12, cur_y, 231, 12, buf, COLOR_BEHAVIOR);
        cur_y += count_wrapped_lines(buf, 231) * 12 + 1;
        snprintf(buf, sizeof(buf), "TRUCO: %s", e->truco);
        bestiary_font_draw_wrapped(fb, 12, cur_y, 231, 12, buf, COLOR_BEHAVIOR);
        cur_y += count_wrapped_lines(buf, 231) * 12 + 2;
    } else {
        bestiary_font_draw_wrapped(fb, 12, cur_y, 231, 12, e->behavior, COLOR_BEHAVIOR);
        cur_y += count_wrapped_lines(e->behavior, 231) * 12 + 6;
    }

    bestiary_font_draw_wrapped(fb, 12, cur_y, 231, 12, e->lore, COLOR_WARM_GRAY);
    int lore_lines = count_wrapped_lines(e->lore, 231);
    cur_y += lore_lines * 12 + 3;

    bestiary_font_draw_wrapped(fb, 12, cur_y, 231, 12, e->quote, COLOR_QUOTE);

    /* Bottom navigation bar separator */
    uint16_t *bar_row = fb + (158 << 8);
    for (int x = 12; x <= 243; x++) bar_row[x] = COLOR_SEPARATOR;

    /* Bottom buttons */
    bestiary_font_draw_utf8(fb, 14, 166, "< Ant", COLOR_BUTTON);

    int bw = bestiary_font_measure_utf8("Volver (B)");
    int bx = (BESTIARY_SCREEN_W - bw) >> 1;
    bestiary_font_draw_utf8(fb, bx, 166, "Volver (B)", COLOR_BUTTON);

    int sw = bestiary_font_measure_utf8("Sig >");
    bestiary_font_draw_utf8(fb, 242 - sw, 166, "Sig >", COLOR_BUTTON);
}

static int compute_anim_frame(int entry_idx, uint32_t anim_tick) {
    if (entry_idx == 0) {
        /* Corazón Abierto (8 frames: f7 -> f0 with pause at f0 and back, ~50% slower) */
        uint32_t t = anim_tick % 160;
        if (t < 56) return 7 - (int)(t / 7);
        if (t < 92) return 0;
        if (t < 148) return (int)((t - 92) / 7);
        return 7;
    } else if (entry_idx == 1) {
        /* Exvoto (8 frames walk loop, ~50% slower) */
        return (int)((anim_tick / 7) % 8);
    } else if (entry_idx == 2) {
        /* Cireneo (8 frames hunched walk loop, ~50% slower) */
        return (int)((anim_tick / 8) % 8);
    } else if (entry_idx == 3) {
        /* Ojo del Tribunal (16 frames: 2 walk cycles per 1 slow lantern sweep) */
        int nf = (s_portrait_valid && s_portrait_loaded_entry == 3 && s_portrait_hdr.num_frames > 0)
            ? (int)s_portrait_hdr.num_frames : 8;
        return (int)((anim_tick / 8) % (uint32_t)nf);
    } else if (entry_idx == 4) {
        /* Abanderado (8 frames walk loop with staff) */
        return (int)((anim_tick / 7) % 8);
    }
    return 0;
}

static void clear_portrait_union_box(uint16_t *fb) {
    if (!fb || !s_portrait_valid) return;
    const BestiaryDirHeader *dh = (const BestiaryDirHeader *)s_portrait_buf;
    int u_cx = (dh->u_min_x + dh->u_max_x) >> 1;
    int u_cy = (dh->u_min_y + dh->u_max_y) >> 1;
    int canvas_x = 128 - u_cx;
    int canvas_y = 96 - u_cy;
    int x0 = canvas_x + dh->u_min_x;
    int y0 = canvas_y + dh->u_min_y;
    int x1 = canvas_x + dh->u_max_x;
    int y1 = canvas_y + dh->u_max_y;
    if (x0 < 5) x0 = 5;
    if (y0 < 5) y0 = 5;
    if (x1 > 250) x1 = 250;
    if (y1 > 186) y1 = 186;
    for (int y = y0; y <= y1; y++) {
        uint16_t *row = fb + (y << 8);
        for (int x = x0; x <= x1; x++) {
            row[x] = COLOR_BLACK_OPAQUE;
        }
    }
}

static void draw_top_character(uint16_t *fb, int entry_idx, int dir, int frame, int full_clear) {
    if (!fb || entry_idx < 0 || entry_idx >= BESTIARY_NUM_ENTRIES) return;
    if (full_clear || !s_portrait_valid || s_portrait_loaded_entry != entry_idx || s_portrait_loaded_dir != (dir & 7)) {
        uint32_t black_pair = 0x80008000;
        swiFastCopy(&black_pair, fb, COPY_MODE_FILL | (BESTIARY_SCREEN_W * BESTIARY_SCREEN_H * 2 / 4));
        draw_border_rect(fb, COLOR_BORDER);
    } else {
        clear_portrait_union_box(fb);
    }

    if (s_portrait_valid && s_portrait_loaded_entry == entry_idx && s_portrait_loaded_dir == (dir & 7)) {
        draw_portrait_frame_160(fb, frame);
    } else {
        /* Fallback */
        draw_fallback_sprite_2x(fb, entry_idx, (uint32_t)frame * 6u);
    }

    /* Orientation hint in bottom-right corner of top screen */
    char hint[24];
    snprintf(hint, sizeof(hint), "< > Rotar (%s)", s_dir_names[dir & 7]);
    int hw = bestiary_font_measure_utf8(hint);
    bestiary_font_draw_utf8(fb, 248 - hw, 172, hint, COLOR_HINT);
}

void bestiary_run(uint16_t *top_page, uint16_t *bot_page_a, uint16_t *bot_page_b,
                  int *bot_active_page_idx, void (*vblank_flip_fn)(void)) {
    if (!top_page || !bot_page_a || !bot_page_b) return;

    g_bestiary_debug.active = 1;
    g_bestiary_debug.trigger = 0;
    g_bestiary_debug.entry_index = 0;
    g_bestiary_debug.frame_count = 0;

    int cur_entry = 0;
    int cur_dir = 0;
    uint32_t anim_tick = 0;
    int prev_touch_down = 0;

    /* Load initial high-res portrait */
    load_portrait_direction(cur_entry, cur_dir);

    /* Render initial cards to both bottom buffers and wait for VBlank before drawing single-buffered top_page */
    draw_bottom_card(bot_page_a, cur_entry);
    draw_bottom_card(bot_page_b, cur_entry);

    if (vblank_flip_fn) {
        vblank_flip_fn();
    } else {
        swiWaitForVBlank();
    }

    int cur_frame = compute_anim_frame(cur_entry, anim_tick);
    draw_top_character(top_page, cur_entry, cur_dir, cur_frame, 1);
    int prev_drawn_entry = cur_entry;
    int prev_drawn_dir = cur_dir;
    int prev_drawn_frame = cur_frame;
    int bot_dirty = 0;

    while (1) {
        g_bestiary_debug.frame_count++;

        scanKeys();
        uint32_t keys_down = keysDown();
        uint32_t keys_held = keysHeld();
        touchPosition touch;
        touchRead(&touch);

        int touch_down = (keys_held & KEY_TOUCH) && (touch.px < BESTIARY_SCREEN_W) && (touch.py < BESTIARY_SCREEN_H);
        int touch_pressed = touch_down && !prev_touch_down;
        prev_touch_down = touch_down;

        /* Exit check: B button, START, or touch 'Volver (B)' */
        int exit_requested = (keys_down & (KEY_B | KEY_START)) != 0;
        if (touch_pressed && touch.py >= 156 && touch.py <= 188 && touch.px >= 80 && touch.px <= 176) {
            exit_requested = 1;
        }

        if (exit_requested) {
            break;
        }

        /* 1. Entry Navigation: L / R triggers, UP / DOWN dpad, or touch '< Ant' / 'Sig >' */
        int nav_entry = 0;
        if (keys_down & (KEY_L | KEY_UP)) nav_entry = -1;
        if (keys_down & (KEY_R | KEY_DOWN)) nav_entry = 1;

        if (touch_pressed && touch.py >= 156 && touch.py <= 188) {
            if (touch.px >= 4 && touch.px <= 64) nav_entry = -1;
            else if (touch.px >= 192 && touch.px <= 252) nav_entry = 1;
        }

        if (nav_entry != 0) {
            cur_entry = (cur_entry + nav_entry + BESTIARY_NUM_ENTRIES) % BESTIARY_NUM_ENTRIES;
            g_bestiary_debug.entry_index = (uint32_t)cur_entry;
            cur_dir = 0; /* Reset to front view on card change */
            anim_tick = 0;
            load_portrait_direction(cur_entry, cur_dir);
            bot_dirty = 2; /* Redraw both buffer pages */
        }

        /* 2. Character Rotation: LEFT / RIGHT dpad */
        int nav_rot = 0;
        if (keys_down & KEY_LEFT) nav_rot = -1;
        if (keys_down & KEY_RIGHT) nav_rot = 1;

        if (nav_rot != 0) {
            cur_dir = (cur_dir + nav_rot + 8) & 7;
            load_portrait_direction(cur_entry, cur_dir);
        }

        /* Update bottom screen (2-page buffered) before VBlank */
        if (bot_dirty > 0) {
            uint16_t *target_bot = bot_page_a;
            if (bot_active_page_idx && *bot_active_page_idx == 8) {
                target_bot = bot_page_b;
            } else if (bot_active_page_idx && *bot_active_page_idx == 24) {
                target_bot = bot_page_a;
            }
            draw_bottom_card(target_bot, cur_entry);
            bot_dirty--;
        }

        anim_tick++;
        cur_frame = compute_anim_frame(cur_entry, anim_tick);

        /* Wait for VBlank, then draw single-buffered top_page at the start of VBlank (zero tearing) */
        if (vblank_flip_fn) {
            vblank_flip_fn();
        } else {
            swiWaitForVBlank();
        }

        if (cur_entry != prev_drawn_entry || cur_dir != prev_drawn_dir || cur_frame != prev_drawn_frame) {
            int full_clear = (cur_entry != prev_drawn_entry || cur_dir != prev_drawn_dir);
            draw_top_character(top_page, cur_entry, cur_dir, cur_frame, full_clear);
            prev_drawn_entry = cur_entry;
            prev_drawn_dir = cur_dir;
            prev_drawn_frame = cur_frame;
        }
    }

    /* Clean exit: clear bitmap buffers to 0x0000 (transparent) without stutter */
    uint32_t zero = 0;
    swiFastCopy(&zero, top_page, COPY_MODE_FILL | (BESTIARY_SCREEN_W * BESTIARY_SCREEN_H * 2 / 4));
    swiFastCopy(&zero, bot_page_a, COPY_MODE_FILL | (BESTIARY_SCREEN_W * BESTIARY_SCREEN_H * 2 / 4));
    swiFastCopy(&zero, bot_page_b, COPY_MODE_FILL | (BESTIARY_SCREEN_W * BESTIARY_SCREEN_H * 2 / 4));

    if (vblank_flip_fn) {
        vblank_flip_fn();
    } else {
        swiWaitForVBlank();
    }

    s_portrait_loaded_entry = -1;
    s_portrait_loaded_dir = -1;
    s_portrait_valid = 0;
    g_bestiary_debug.active = 0;
}
