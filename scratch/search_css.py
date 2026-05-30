import re

with open("d:/QR/frontend/src/features/events/pages/events.css", "r", encoding="utf-8") as f:
    content = f.read()

# Search for blocks starting with .inv-design-canvas
matches = re.finditer(r"\.inv-design-canvas[^{]*\{[^}]*\}", content)
print("Matches in events.css:")
for m in matches:
    print(m.group(0))
    print("-" * 40)
