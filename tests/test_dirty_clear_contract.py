import re
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "source" / "main.c"


class DirtyClearContractTest(unittest.TestCase):
    def test_span_clear_uses_arm_stmia_bursts(self):
        source = SOURCE.read_text(encoding="utf-8")

        burst = re.search(
            r'__attribute__\(\(target\("arm"\), optimize\("O3"\), noinline\)\)\s*'
            r"(?:ITCM_CODE\s*)?static void zero_words_burst\(uint32_t \*p, int n\) \{(.*?)\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(burst, "zero_words_burst must be an ARM noinline routine")
        self.assertIn("stmia %[q]!, {r2-r8, r12}", burst.group(1))

        clear = re.search(
            r"static void clear_dirty_spans\(uint16_t \*page, DirtySpan \*spans\) \{(.*?)\n#if DIRTY_VERIFY",
            source,
            re.S,
        )
        self.assertIsNotNone(clear)
        body = clear.group(1)
        self.assertIn("zero_words_burst((uint32_t *)&page[y * SCREEN_W + x0], (x1 - x0) >> 1);", body)
        self.assertNotIn("volatile uint32_t *p", body)
        self.assertNotIn("*p++ = 0", body)


if __name__ == "__main__":
    unittest.main()
