#include "arpg_balance.h"

#if ARPG_BOT
volatile ArpgBalance g_bal;      // all zero: no override (arpg_balance.h)
#else
typedef int arpg_balance_translation_unit_not_empty;
#endif
