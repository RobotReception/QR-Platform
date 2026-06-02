import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
import arabic_reshaper.letters as letters
from bidi.algorithm import get_display

# Build translation dictionary: Isolated form -> Unshaped form
isolated_to_unshaped = {}
for unshaped, forms in letters.LETTERS_ARABIC.items():
    isolated = forms[letters.ISOLATED]
    if isolated:
        isolated_to_unshaped[isolated] = unshaped

if hasattr(letters, 'LETTERS_ARABIC_V2'):
    for unshaped, forms in letters.LETTERS_ARABIC_V2.items():
        isolated = forms[letters.ISOLATED]
        if isolated:
            isolated_to_unshaped[isolated] = unshaped

def fix_isolated_forms(text):
    # Replace each character if it is in the isolated_to_unshaped dictionary
    return "".join(isolated_to_unshaped.get(c, c) for c in text)

def render_test_text(text, font_path, output_path):
    # Reshape and BiDi
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    
    # Fix isolated forms (replace with standard forms)
    fixed_text = fix_isolated_forms(bidi_text)
    
    print(f"Original bidi: {repr(bidi_text)}")
    print(f"Fixed bidi:    {repr(fixed_text)}")
    
    img = Image.new("RGBA", (800, 100), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font = ImageFont.truetype(font_path, 32)
    draw.text((50, 30), fixed_text, font=font, fill=(0, 0, 0, 255))
    img.save(output_path)
    print(f"Rendered {font_path} -> {output_path}")

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    render_test_text("المهندس حمد الشهري", "fonts/Cairo-Regular.ttf", "scratch/test_cairo_fixed.png")
    render_test_text("الدكتورة سارة العتيبي", "fonts/Cairo-Regular.ttf", "scratch/test_cairo_fixed_2.png")
