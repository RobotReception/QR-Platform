"""Crop and zoom into the 4 name positions to verify names are different."""
import sys
sys.path.insert(0, ".")
from PIL import Image

img = Image.open("scratch/test_render_output.png")
w, h = img.size
print(f"Image size: {w}x{h}")

# Crop around each name position
# slot 0: px=(102,584,244,88) - top-left
# slot 1: px=(722,584,244,88) - top-right
# slot 2: px=(102,1461,244,88) - bottom-left
# slot 3: px=(722,1461,244,88) - bottom-right

regions = [
    ("slot0_top_left", (60, 550, 380, 700)),
    ("slot1_top_right", (680, 550, 1000, 700)),
    ("slot2_bottom_left", (60, 1425, 380, 1575)),
    ("slot3_bottom_right", (680, 1425, 1000, 1575)),
]

for name, box in regions:
    crop = img.crop(box)
    # Scale up 3x for visibility
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.NEAREST)
    path = f"scratch/{name}.png"
    crop.save(path)
    print(f"Saved: {path} ({crop.width}x{crop.height})")
