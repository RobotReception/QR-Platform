import sys
import arabic_reshaper.letters as letters

sys.stdout.reconfigure(encoding='utf-8')

print("LETTERS_ARABIC type:", type(letters.LETTERS_ARABIC))
print("First few items in LETTERS_ARABIC:")
count = 0
for k, v in letters.LETTERS_ARABIC.items():
    print(f"Key: {repr(k)} -> Value: {v}")
    count += 1
    if count >= 10:
        break

# Let's inspect the indices/keys used for forms
print("\nletters.ISOLATED:", repr(letters.ISOLATED))
print("letters.UNSHAPED:", repr(letters.UNSHAPED))
print("letters.FINAL:", repr(letters.FINAL))
print("letters.INITIAL:", repr(letters.INITIAL))
print("letters.MEDIAL:", repr(letters.MEDIAL))
