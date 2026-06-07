import os

filepath = r"d:\QR\frontend\src\features\events\components\EventInvitationsTab.tsx"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
# Lines are 1-indexed. Let's find the exact line indices.
# Line 196 in 1-based indexing is index 195.
# Line 1714 in 1-based indexing is index 1713.
# Let's verify line contents to be 100% sure.
print(f"Line 192 (0-indexed 191): {lines[191].strip()}")
print(f"Line 197 (0-indexed 196): {lines[196].strip()}")
print(f"Line 1714 (0-indexed 1713): {lines[1713].strip()}")
print(f"Line 1715 (0-indexed 1714): {lines[1714].strip()}")

# We want to keep up to line 196 (index 195) inclusive, and from line 1715 (index 1714) inclusive.
# So new_lines = lines[:196] + lines[1714:]
new_lines = lines[:196] + lines[1714:]

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Finished cleaning EventInvitationsTab.tsx!")
