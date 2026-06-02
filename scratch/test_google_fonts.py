import urllib.request
import os
import sys

# Force utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

def download_file(url, dest):
    print(f"Downloading {url} to {dest}...")
    try:
        urllib.request.urlretrieve(url, dest)
        print("Success!")
        return True
    except Exception as e:
        print(f"Failed to download: {e}")
        return False

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
    
    # Official static fonts URLs
    cairo_url = "https://github.com/google/fonts/raw/main/ofl/cairo/static/Cairo-Regular.ttf"
    tajawal_url = "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Regular.ttf"
    
    cairo_dest = "scratch/Cairo-Regular-Google.ttf"
    tajawal_dest = "scratch/Tajawal-Regular-Google.ttf"
    
    download_file(cairo_url, cairo_dest)
    download_file(tajawal_url, tajawal_dest)
    
    if os.path.exists(cairo_dest):
        render_test_text("المهندس حمد الشهري", cairo_dest, "scratch/test_cairo_google.png")
    if os.path.exists(tajawal_dest):
        render_test_text("المهندس حمد الشهري", tajawal_dest, "scratch/test_tajawal_google.png")
