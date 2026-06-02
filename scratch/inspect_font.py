import sys
from fontTools.ttLib import TTFont

sys.stdout.reconfigure(encoding='utf-8')

font = TTFont("fonts/Cairo-Regular.ttf")
glyph_names = font.getGlyphOrder()

print("Total glyphs:", len(glyph_names))
print("First 20 glyph names:", glyph_names[:20])

# Find glyphs starting with 'uniFE' or containing 'FE'
fe_glyphs = [name for name in glyph_names if "fe" in name.lower()]
print("FE glyphs found:", len(fe_glyphs))
if fe_glyphs:
    print("Some FE glyph names:", fe_glyphs[:50])

# Let's check for names containing 'alif' or 'baa' or 'isol' or 'init' or 'medi' or 'fina'
arabic_glyphs = [name for name in glyph_names if any(x in name.lower() for x in ["alif", "baa", "isol", "init", "medi", "fina", "arab"])]
print("Arabic-related glyph names count:", len(arabic_glyphs))
if arabic_glyphs:
    print("Some Arabic glyph names:", arabic_glyphs[:50])
