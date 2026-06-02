import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

def render_test_text(text, font_path, output_path):
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    
    img = Image.new("RGBA", (800, 100), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(font_path, 32)
        draw.text((50, 30), bidi_text, font=font, fill=(0, 0, 0, 255))
        img.save(output_path)
        print(f"Rendered {font_path} -> {output_path}")
    except Exception as e:
        print(f"Failed {font_path}: {e}")

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    fonts = [
        "fonts/Cairo-Regular.ttf",
        "fonts/Tajawal-Regular.ttf",
        "fonts/Amiri-Regular.ttf",
        "fonts/NotoSansArabic-Regular.ttf",
        "fonts/Almarai-Regular.ttf",
        "fonts/Alexandria-Regular.ttf"
    ]
    
    for f in fonts:
        basename = os.path.splitext(os.path.basename(f))[0]
        render_test_text("المهندس حمد الشهري", f, f"scratch/test_{basename}.png")
