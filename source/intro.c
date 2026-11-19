#include "intro.h"
#include "bestiary_font.h"
#include <nds.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SW 256
#define SH 192
#define N_CARDS 6

#define COL_BORDER (RGB15(8, 8, 8) | 0x8000)
#define COL_SEP    (RGB15(6, 6, 6) | 0x8000)
#define COL_IVORY  (RGB15(29, 28, 26) | 0x8000)
#define COL_WARM   (RGB15(20, 19, 18) | 0x8000)
#define COL_BTN    (RGB15(22, 21, 20) | 0x8000)
#define COL_DIM    (RGB15(12, 12, 12) | 0x8000)

typedef struct {
    const char *title;
    const char *text;
} IntroCard;

static const IntroCard s_cards[N_CARDS] = {
    { "La catedral",
      "Cada sala tiene sus caídos. Límpiala y la reja se levanta; al entrar, cae detrás de ti." },
    { "Moverse y apuntar",
      "La cruceta mueve. El lápiz apunta; mantenerlo pulsado carga el disparo y al soltarlo sale el rayo." },
    { "Coberturas",
      "Pégate a un banco o a unos sacos y te agachas solo. Andas más despacio, y el Ojo no te ve tras ellos." },
    { "Rematar",
      "Un disparo deja tambaleando al caído. Acércate y pulsa L para rematarlo: durante la ejecución y un segundo después eres invulnerable, y el rayo queda recargado." },
    { "Relicarios",
      "Rompe a tiros los relicarios de las salas y elige un Don: una mejora para esta partida." },
    { "Vida",
      "Tienes 5 Sagrados Corazones. Los caídos a veces sueltan uno que cura 1 si lo pisas. Tras un golpe tienes un segundo de invulnerabilidad." },
};

static void fill_rect(uint16_t *fb, int x0, int y0, int w, int h, uint16_t c) {
    for (int y = y0; y < y0 + h; y++) {
        if ((unsigned)y >= SH) continue;
        for (int x = x0; x < x0 + w; x++) {
            if ((unsigned)x < SW) fb[y * SW + x] = c;
        }
    }
}

static void clear_black(uint16_t *fb) {
    uint32_t black_pair = 0x80008000;
    swiFastCopy(&black_pair, fb, COPY_MODE_FILL | (SW * SH * 2 / 4));
    fill_rect(fb, 4, 4, 248, 1, COL_BORDER);
    fill_rect(fb, 4, 187, 248, 1, COL_BORDER);
    fill_rect(fb, 4, 4, 1, 184, COL_BORDER);
    fill_rect(fb, 251, 4, 1, 184, COL_BORDER);
}

/* ---- Bucles de video de la pantalla inferior del juego real --------------------------------------
 * Formato (tools/gen_intro_clips.py), little endian:
 *   u16 magic 0x4956 | u16 n (imagenes del bucle) | u32 max_rec | u32 max_dec | u32 off[n + 2]  (off[n + 1] = fin)
 *   registro 0 = imagen completa (96 KB de pixeles, LZ10); 1..n-1 = delta con la anterior; n = delta de la
 *   ultima a la imagen 0. Secuencia reproducida: 0, 1, ..., n, 1, 2, ..., n, 1, ...  (n imagenes por vuelta).
 *   delta = s8 dx, s8 dy (la imagen anterior se desplaza: nueva[i] = vieja[i + dy*256 + dx]) y palabras u16:
 *   tipo << 14 | cuenta; 0 = saltar, 1 = literales (siguen `cuenta` pixeles), 2 = repetir (sigue 1 pixel).
 *   Un delta que empieza por 0x10 va comprimido con LZ10 (BIOS); dx esta en [-6, 6]. Pixeles BGR555 con el
 *   bit 15 puesto: copia directa a VRAM.
 * La RAM (imagen de 96 KB + registro + descompresion) se pide al entrar en la tarjeta y se libera al salir. */
#define VID_MAGIC 0x4956
#define VID_MAX_N 64
#define VID_PIXELS (SW * SH)

static const char *const s_clip_names[N_CARDS] = { "catedral", "apuntar", "cobertura", "remate", "relicario", "corazon" };

typedef struct {
    FILE *f;
    uint16_t *fb;          /* imagen actual, VID_PIXELS pixeles */
    uint8_t *rec;          /* registro leido (como esta en el archivo) */
    uint8_t *dec;          /* registro de delta descomprimido */
    uint32_t off[VID_MAX_N + 2];
    int n;
    int next;              /* proximo registro a descodificar */
} Video;

static Video s_vid;
static void video_close(void) {
    if (s_vid.f) fclose(s_vid.f);
    free(s_vid.fb);
    free(s_vid.rec);
    free(s_vid.dec);
    memset(&s_vid, 0, sizeof(s_vid));
}

static int video_open(int card) {
    video_close();
    char path[48];
    snprintf(path, sizeof(path), "nitro:/intro/%s.bin", s_clip_names[card]);
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    uint16_t magic, n;
    uint32_t max_rec, max_dec;
    if (fread(&magic, 2, 1, f) != 1 || fread(&n, 2, 1, f) != 1 || fread(&max_rec, 4, 1, f) != 1 ||
        fread(&max_dec, 4, 1, f) != 1 ||
        magic != VID_MAGIC || n < 2 || n > VID_MAX_N || max_rec > 256 * 1024 || max_dec > 256 * 1024 ||
        fread(s_vid.off, 4, (size_t)n + 2, f) != (size_t)n + 2) {
        fclose(f);
        return 0;
    }
    s_vid.f = f;
    s_vid.n = n;
    s_vid.fb = (uint16_t *)malloc(VID_PIXELS * 2);
    s_vid.rec = (uint8_t *)malloc(max_rec + 4);
    s_vid.dec = (uint8_t *)malloc(max_dec + 4);
    if (!s_vid.fb || !s_vid.rec || !s_vid.dec) {
        video_close();
        return 0;
    }
    memset(s_vid.fb, 0, VID_PIXELS * 2);
    s_vid.next = 0;
    return 1;
}

/* Descodifica el registro siguiente sobre la imagen. Sin float ni divisiones. */
__attribute__((target("arm"), optimize("O3")))
static void video_step(void) {
    if (!s_vid.f) return;
    int idx = s_vid.next;
    s_vid.next = (idx == s_vid.n) ? 1 : idx + 1;
    uint32_t size = s_vid.off[idx + 1] - s_vid.off[idx];
    if (size < 2 || fseek(s_vid.f, (long)s_vid.off[idx], SEEK_SET) != 0 ||
        fread(s_vid.rec, 1, size, s_vid.f) != size) return;

    uint16_t *fb = s_vid.fb;
    if (idx == 0) {                              /* imagen completa: la BIOS la descomprime directa */
        swiDecompressLZSSWram(s_vid.rec, fb);
        return;
    }
    const uint8_t *rec = s_vid.rec;
    if (rec[0] == 0x10) {
        swiDecompressLZSSWram(rec, s_vid.dec);
        rec = s_vid.dec;
        size = (uint32_t)(*(const uint32_t *)s_vid.rec >> 8);
    }
    int off = ((int)(int8_t)rec[1] << 8) + (int)(int8_t)rec[0];
    if (off > 0) memmove(fb, fb + off, (size_t)(VID_PIXELS - off) * 2);
    else if (off < 0) memmove(fb - off, fb, (size_t)(VID_PIXELS + off) * 2);

    const uint16_t *w = (const uint16_t *)(rec + 2);
    const uint16_t *end = (const uint16_t *)(rec + size);
    int pos = 0;
    while (w < end && pos < VID_PIXELS) {
        uint32_t op = *w++;
        int cnt = (int)(op & 0x3fff);
        if (pos + cnt > VID_PIXELS) break;
        uint32_t type = op >> 14;
        if (type == 1) {
            memcpy(fb + pos, w, (size_t)cnt * 2);
            w += cnt;
        } else if (type == 2) {
            uint16_t v = *w++;
            for (int i = 0; i < cnt; i++) fb[pos + i] = v;
        }
        pos += cnt;
    }
}

static void video_show(uint16_t *top_page) {
    if (!s_vid.fb) {
        uint32_t black = 0x80008000;
        swiFastCopy(&black, top_page, COPY_MODE_FILL | (VID_PIXELS * 2 / 4));
        return;
    }
    swiFastCopy(s_vid.fb, top_page, COPY_MODE_COPY | (VID_PIXELS * 2 / 4));
}

static void draw_bottom(uint16_t *fb, int card) {
    clear_black(fb);
    bestiary_font_draw_utf8(fb, 12, 10, s_cards[card].title, COL_IVORY);
    char pbuf[4] = { (char)('1' + card), '/', (char)('0' + N_CARDS), 0 };
    int pw = bestiary_font_measure_utf8(pbuf);
    bestiary_font_draw_utf8(fb, 244 - pw, 10, pbuf, COL_WARM);
    fill_rect(fb, 12, 24, 232, 1, COL_SEP);
    bestiary_font_draw_wrapped(fb, 12, 34, 231, 14, s_cards[card].text, COL_WARM);
    fill_rect(fb, 12, 158, 232, 1, COL_SEP);

    bestiary_font_draw_utf8(fb, 14, 166, "< Ant", card == 0 ? COL_DIM : COL_BTN);
    int bw = bestiary_font_measure_utf8("Saltar");
    bestiary_font_draw_utf8(fb, (SW - bw) >> 1, 166, "Saltar", COL_BTN);
    const char *nxt = (card == N_CARDS - 1) ? "Empezar" : "Sig >";
    bestiary_font_draw_utf8(fb, 242 - bestiary_font_measure_utf8(nxt), 166, nxt, COL_BTN);
}

static void wait_vblank(void (*fn)(void)) {
    if (fn) fn(); else swiWaitForVBlank();
}

void intro_run(uint16_t *top_page, uint16_t *bot_page_a, uint16_t *bot_page_b,
               int *bot_active_page_idx, void (*vblank_flip_fn)(void)) {
    if (!top_page || !bot_page_a || !bot_page_b) return;

    int card = 0;
    int top_dirty = 1;     /* abrir el bucle de la tarjeta y mostrar su primera imagen */
    int vtick = 0;
    int bot_dirty = 0;
    int prev_touch_down = 1; /* el toque que eligio NUEVA PARTIDA no cuenta */

    draw_bottom(bot_page_a, card);
    draw_bottom(bot_page_b, card);
    wait_vblank(vblank_flip_fn);

    while (1) {
        scanKeys();
        uint32_t keys_down = keysDown();
        uint32_t keys_held = keysHeld();
        touchPosition touch;
        touchRead(&touch);
        int touch_down = (keys_held & KEY_TOUCH) && touch.px < SW && touch.py < SH;
        int touch_pressed = touch_down && !prev_touch_down;
        prev_touch_down = touch_down;

        int step = 0;
        int done = (keys_down & KEY_START) != 0;
        if (keys_down & (KEY_A | KEY_RIGHT | KEY_R)) step = 1;
        if (keys_down & (KEY_B | KEY_LEFT | KEY_L)) step = -1;
        if (touch_pressed && touch.py >= 156 && touch.py <= 188) {
            if (touch.px >= 4 && touch.px <= 64) step = -1;
            else if (touch.px >= 80 && touch.px <= 176) done = 1;
            else if (touch.px >= 192 && touch.px <= 252) step = 1;
        }
        if (done) break;
        if (step > 0 && card == N_CARDS - 1) break;
        if (step != 0 && card + step >= 0) {
            card += step;
            top_dirty = 1;
            bot_dirty = 2;
        }

        if (bot_dirty > 0) {
            uint16_t *target = bot_page_a;
            if (bot_active_page_idx && *bot_active_page_idx == 8) target = bot_page_b;
            draw_bottom(target, card);
            bot_dirty--;
        }

        wait_vblank(vblank_flip_fn);
        if (top_dirty) {
            video_open(card);
            video_step();                       /* imagen completa */
            video_show(top_page);
            video_step();
            vtick = 0;
            top_dirty = 0;
        } else if ((vtick ^= 1) == 0) {         /* 30 imagenes por segundo: una cada 2 vblank */
            video_show(top_page);
            video_step();
        }
    }
    video_close();

    uint32_t zero = 0;
    swiFastCopy(&zero, top_page, COPY_MODE_FILL | (SW * SH * 2 / 4));
    swiFastCopy(&zero, bot_page_a, COPY_MODE_FILL | (SW * SH * 2 / 4));
    swiFastCopy(&zero, bot_page_b, COPY_MODE_FILL | (SW * SH * 2 / 4));
    wait_vblank(vblank_flip_fn);
}
