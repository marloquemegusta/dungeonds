// Minimal stand-in for libnds so the pure game logic can be compiled and tested on the host.
#ifndef HOST_NDS_H
#define HOST_NDS_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t s32;
#define BIT(n) (1u << (n))
#define RGB15(r, g, b) ((r) | ((g) << 5) | ((b) << 10))
#endif
