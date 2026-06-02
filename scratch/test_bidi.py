import sys
import arabic_reshaper
from bidi.algorithm import get_display

sys.stdout.reconfigure(encoding='utf-8')

test_cases = [
    "المهندس حمد الشهري",
    "المهندس حمد الشهري 123",
    "المهندس حمد الشهري - VIP",
    "الدكتورة سارة العتيبي",
    "الدكتور مساعد العتيبي",
    "المهندس حمد الشهري\xa0",
    " المهندس حمد الشهري "
]

for idx, case in enumerate(test_cases):
    reshaped = arabic_reshaper.reshape(case)
    bidi_text = get_display(reshaped)
    print(f"\nCase {idx}: {repr(case)}")
    print(f"Bidi: {repr(bidi_text)}")
    for j, char in enumerate(bidi_text):
        o = ord(char)
        if o < 128 or o in (0xa0, 0x200c, 0x200d, 0x200e, 0x200f) or 0x202a <= o <= 0x202e:
            print(f"  Index {j}: char={repr(char)}, hex={hex(o)}")
