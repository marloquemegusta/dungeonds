#include "crashlog.h"

#if CRASHLOG_ENABLED

#include <nds.h>
#include <fat.h>
#include <stdio.h>

#define CRASHLOG_RING 96

typedef struct {
    uint32_t frame;
    uint16_t code;
    int32_t a, b;
} Crumb;

static Crumb s_ring[CRASHLOG_RING];
static uint32_t s_head;
static uint32_t s_frame;
static int s_sd_ok;

static PrintConsole s_con_main, s_con_sub;

static FILE *s_live;
static char s_live_buf[8192];

// Rewrites a fixed-size snapshot of the breadcrumb ring once per second, so a
// log survives even if the exception handler itself cannot run.
static void flush_live_log(void) {
    uint32_t n = s_head < 64 ? s_head : 64;
    int len = snprintf(s_live_buf, sizeof(s_live_buf), "LIVE frame=%lu crumbs(oldest first: frame code a b)\r\n",
                       (unsigned long)s_frame);
    for (uint32_t i = 0; i < n && len < (int)sizeof(s_live_buf) - 64; i++) {
        const Crumb *c = &s_ring[(s_head - n + i) % CRASHLOG_RING];
        len += snprintf(s_live_buf + len, sizeof(s_live_buf) - len, "%lu %u %ld %ld\r\n",
                        (unsigned long)c->frame, c->code, (long)c->a, (long)c->b);
    }
    for (int i = len; i < (int)sizeof(s_live_buf); i++) s_live_buf[i] = ' ';
    rewind(s_live);
    fwrite(s_live_buf, 1, sizeof(s_live_buf), s_live);
    fflush(s_live);
}

void crashlog_set_frame(uint32_t frame) {
    s_frame = frame;
    if (s_live && (frame % 60) == 0) flush_live_log();
}

void crashlog_mark(uint16_t code, int32_t a, int32_t b) {
    Crumb *c = &s_ring[s_head++ % CRASHLOG_RING];
    c->frame = s_frame;
    c->code = code;
    c->a = a;
    c->b = b;
}

static void write_report(FILE *f) {
    fprintf(f, "DUNGEONDS CRASH\r\n");
    fprintf(f, "frame=%lu\r\n", (unsigned long)s_frame);
    for (int i = 0; i < 16; i++)
        fprintf(f, "r%d=%08lX\r\n", i, (unsigned long)exceptionRegisters[i]);
    fprintf(f, "(faulting instruction ~ r15-8; resolve in the .map)\r\n");
    uint32_t n = s_head < CRASHLOG_RING ? s_head : CRASHLOG_RING;
    fprintf(f, "last %lu breadcrumbs (oldest first): frame code a b\r\n", (unsigned long)n);
    for (uint32_t i = 0; i < n; i++) {
        const Crumb *c = &s_ring[(s_head - n + i) % CRASHLOG_RING];
        fprintf(f, "%lu %u %ld %ld\r\n", (unsigned long)c->frame, c->code, (long)c->a, (long)c->b);
    }
}

static void print_report(void) {
    printf("EXCEPTION frame %lu SD:%s\n", (unsigned long)s_frame, s_sd_ok ? "yes" : "no");
    printf("pc=%08lX lr=%08lX sp=%08lX\n", (unsigned long)exceptionRegisters[15],
           (unsigned long)exceptionRegisters[14], (unsigned long)exceptionRegisters[13]);
    printf("r0=%08lX r1=%08lX\nr2=%08lX r3=%08lX\n", (unsigned long)exceptionRegisters[0],
           (unsigned long)exceptionRegisters[1], (unsigned long)exceptionRegisters[2],
           (unsigned long)exceptionRegisters[3]);
    uint32_t n = s_head < 12 ? s_head : 12;
    for (uint32_t i = 0; i < n; i++) {
        const Crumb *c = &s_ring[(s_head - n + i) % CRASHLOG_RING];
        printf("%lu:%u %ld %ld\n", (unsigned long)c->frame, c->code, (long)c->a, (long)c->b);
    }
}

void crashlog_report(void) __attribute__((noreturn, used));
void crashlog_report(void) {
    // Text consoles on both engines: the game drives them in a layout that differs
    // from the default, so the report is shown wherever the user is looking.
    videoSetMode(MODE_0_2D);
    vramSetBankA(VRAM_A_MAIN_BG);
    consoleInit(&s_con_main, 0, BgType_Text4bpp, BgSize_T_256x256, 15, 0, true, true);
    setBackdropColor(RGB15(31, 0, 0));
    consoleSelect(&s_con_main);
    print_report();

    videoSetModeSub(MODE_0_2D);
    vramSetBankC(VRAM_C_SUB_BG);
    consoleInit(&s_con_sub, 0, BgType_Text4bpp, BgSize_T_256x256, 15, 0, false, true);
    setBackdropColorSub(RGB15(31, 0, 0));
    consoleSelect(&s_con_sub);
    print_report();

    // Screen first: the SD write can hang if the fault interrupted a disk access.
    if (s_sd_ok) {
        FILE *f = fopen("/dungeonds_crash.log", "wb");
        if (f) {
            write_report(f);
            fclose(f);
            printf("SD log written\n");
        }
    }
    while (1) swiWaitForVBlank();
}

// The stack libnds hands to user handlers is tiny and printf needs far more, so
// switch to a private stack before reporting.
uint64_t crashlog_stack[1024] __attribute__((used)); // 8 KB

__attribute__((naked, target("arm"), noinline))
static void crash_handler(void) {
    __asm__ volatile(
        "ldr sp, =crashlog_stack + 8192\n"
        "b crashlog_report\n");
}

__attribute__((target("arm"), noinline))
void crashlog_poll_test_trigger(void) {
    const uint32_t combo_direct = KEY_L | KEY_R | KEY_START;
    const uint32_t combo_fault = KEY_L | KEY_R | KEY_SELECT;
    // L+R+START runs the report path directly (checks screens and SD log);
    // L+R+SELECT raises a real CPU exception through libnds.
    if ((keysHeld() & combo_direct) == combo_direct) {
        crashlog_mark(98, 0, 0);
        crashlog_report();
    }
    if ((keysHeld() & combo_fault) == combo_fault) {
        crashlog_mark(99, 0, 0);
        // Permanently undefined ARM instruction: raises the same exception path
        // as a real abort, but behaves identically on hardware and in the emulator.
        __asm__ volatile(".word 0xE7F000F0");
    }
}

int crashlog_sd_ready(void) { return s_sd_ok; }

void crashlog_init(void) {
    s_sd_ok = fatInitDefault();
    if (s_sd_ok) s_live = fopen("/dungeonds_live.log", "wb");
    setExceptionHandler(crash_handler);
}

#endif
