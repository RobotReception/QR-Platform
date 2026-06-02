import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont
from app.services.render_service import _reshape_arabic

def test_integration_render(text, font_path, output_path):
    # Reshape using the actual project function
    reshaped_bidi = _reshape_arabic(text)
    
    print(f"Integration shaped text: {repr(reshaped_bidi)}")
    
    img = Image.new("RGBA", (800, 100), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    font = ImageFont.truetype(font_path, 32)
    draw.text((50, 30), reshaped_bidi, font=font, fill=(0, 0, 0, 255))
    img.save(output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    test_integration_render("المهندس حمد الشهري", "fonts/Cairo-Regular.ttf", "scratch/test_integration_cairo.png")
    test_integration_render("الدكتورة سارة العتيبي", "fonts/Cairo-Regular.ttf", "scratch/test_integration_cairo_2.png")
