"""
Compare editor CSS positioning vs backend Pillow positioning for the text element.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Data from DB
canvas_w = 1240
canvas_h = 1754

# Text element (dynamic_text / اسم الضيف)
text_elem = {
    "x": 0.0573,
    "y": 0.3245,
    "width": 0.3573,
    "height": 0.0783,
    "font_size": 21,
    "text_align": "center",
}

# Backend: _element_box_px calculation
left = round(text_elem["x"] * canvas_w)
top = round(text_elem["y"] * canvas_h)
ew = round(text_elem["width"] * canvas_w)
eh = round(text_elem["height"] * canvas_h)

print("=" * 60)
print("BACKEND (Pillow) calculations:")
print(f"  left   = {text_elem['x']:.4f} * {canvas_w} = {left} px")
print(f"  top    = {text_elem['y']:.4f} * {canvas_h} = {top} px")
print(f"  width  = {text_elem['width']:.4f} * {canvas_w} = {ew} px")
print(f"  height = {text_elem['height']:.4f} * {canvas_h} = {eh} px")
print(f"  font   = {text_elem['font_size']} px")
print()

# Frontend: CSS positioning
# The editor uses CSS: left/top as percentage of canvas
css_left = text_elem["x"] * 100  # %
css_top = text_elem["y"] * 100   # %
css_width = text_elem["width"] * 100  # %
css_height = text_elem["height"] * 100  # %
css_left_px = text_elem["x"] * canvas_w
css_top_px = text_elem["y"] * canvas_h
css_width_px = text_elem["width"] * canvas_w
css_height_px = text_elem["height"] * canvas_h

print("EDITOR (CSS) calculations:")
print(f"  left   = {css_left:.2f}% = {css_left_px:.1f} px")
print(f"  top    = {css_top:.2f}% = {css_top_px:.1f} px")
print(f"  width  = {css_width:.2f}% = {css_width_px:.1f} px")
print(f"  height = {css_height:.2f}% = {css_height_px:.1f} px")
print(f"  font   = {text_elem['font_size']} px")
print()

# Now check how the frontend renders the element position
# Frontend CSS from EventDesignEditorPage.tsx:
# style={{ left: `${element.x * 100}%`, top: `${element.y * 100}%`, 
#          width: `${element.width * 100}%`, height: `${element.height * 100}%` }}
print("=" * 60)
print("COMPARISON:")
print(f"  Position match: left={left} vs {css_left_px:.1f}, top={top} vs {css_top_px:.1f}")
print(f"  Size match:     w={ew} vs {css_width_px:.1f}, h={eh} vs {css_height_px:.1f}")
print()

# Check the frontend rendering code for the element
print("Checking the frontend element rendering code...")
print("Looking for how CSS position is set...")
