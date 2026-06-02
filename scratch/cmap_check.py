import sys
from fontTools.ttLib import TTFont

sys.stdout.reconfigure(encoding='utf-8')

font = TTFont("fonts/Cairo-Regular.ttf")
cmap = font.getBestCmap()

# Check if any 0xFE.. keys are in cmap
fe_keys = [k for k in cmap.keys() if 0xFE70 <= k <= 0xFEFF or 0xFB50 <= k <= 0xFDFF]
print("Presentation Form keys in CMAP:", len(fe_keys))

# Print mapped values for some uniFE... names
reverse_cmap = {v: k for k, v in cmap.items()}
fe_glyphs = [name for name in font.getGlyphOrder() if name.startswith("uniFE") or name.startswith("uniFB") or name.startswith("uniFC") or name.startswith("uniFD")]

print("\nGlyph mappings for uniFE... glyphs:")
for glyph in fe_glyphs[:20]:
    mapped_unicode = reverse_cmap.get(glyph)
    if mapped_unicode:
        print(f"  {glyph} is mapped to {hex(mapped_unicode)}")
    else:
        print(f"  {glyph} is NOT mapped to any Unicode codepoint!")
