#ifndef CFXPROF_H
#define CFXPROF_H
// Debug-only profile of the Campanero fight (read by scenarios/arpg_campanero_prof.json through the ELF symbol g_cfxp).
// Compiled in only with CFX_PROF=1; otherwise every macro vanishes.
#include <stdint.h>
#ifndef CFX_PROF
#define CFX_PROF 0
#endif
enum {
    CP_RF = 0, CP_PRE, CP_TRAIL, CP_FRONT, CP_GLOW, CP_SPUR, CP_CUT, CP_MOTE, CP_MEMSET, CP_FLUSH,
    CP_UPDATE, CP_MARCH, CP_HIT, CP_CAMP, CP_EMIT, CP_RAISE, CP_EN_NAV, CP_EN_AI, CP_EN_ENC, CP_EN_MODS, CP_EN_ALL,
    CP_OCC_WEAP, CP_OCC_GLIFO, CP_OCC_PUD, CP_OCC_MELT, CP_OCC_ENC,
    CP_MMEFF, CP_MMARGS, CP_SFX, CP_NZ, CP_SPOT, CP_RSFX, CP_PUTT, CP_TGPIF, CP_TWSH, CP_TWPH,
    CP_PUT, CP_PUT_IN, CP_GPIF, CP_WSH, CP_WPH, CP_FRAMES,
    CP_COUNT
};
#if CFX_PROF
#include <nds.h>
// t: summed ticks, mx: max ticks of one call, n: number of calls (for CP_PUT.. : the counter itself)
typedef struct { uint32_t t[CP_COUNT]; uint32_t mx[CP_COUNT]; uint32_t n[CP_COUNT]; uint32_t p[CP_COUNT]; } CfxProf;
extern volatile CfxProf g_cfxp;
#ifndef CFX_PROF_FINE
#define CFX_PROF_FINE 0   // 1: also time every put() and its callees (adds ~60% overhead)
#endif
#define CP_BEGIN(id) uint32_t cp_t_##id = cpuGetTiming(), cp_p_##id = g_cfxp.n[CP_PUT]
#define CP_END(id) do { uint32_t d_ = cpuGetTiming() - cp_t_##id; g_cfxp.t[id] += d_; if (d_ > g_cfxp.mx[id]) g_cfxp.mx[id] = d_; g_cfxp.n[id]++; g_cfxp.p[id] += g_cfxp.n[CP_PUT] - cp_p_##id; } while (0)
#define CP_COUNT_INC(id) (g_cfxp.n[id]++)
#if CFX_PROF_FINE
#define CP_BEGIN_F(id) CP_BEGIN(id)
#define CP_END_F(id) CP_END(id)
#else
#define CP_BEGIN_F(id) ((void)0)
#define CP_END_F(id) ((void)0)
#endif
#else
#define CP_BEGIN(id) ((void)0)
#define CP_END(id) ((void)0)
#define CP_COUNT_INC(id) ((void)0)
#define CP_BEGIN_F(id) ((void)0)
#define CP_END_F(id) ((void)0)
#endif
#endif
