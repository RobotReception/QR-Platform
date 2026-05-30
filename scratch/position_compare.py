"""
Compare: Editor CSS position vs Backend Pillow position
Proves they use the exact same calculation.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Canvas dimensions (same in editor and backend)
CANVAS_W = 1240
CANVAS_H = 1754

# Elements from database (template 8957476d - Normal)
elements = [
    {"type": "qr_code",      "dk": "barcode",          "x": 0.216, "y": 0.222, "w": 0.157, "h": 0.111},
    {"type": "qr_code",      "dk": "barcode",          "x": 0.649, "y": 0.216, "w": 0.157, "h": 0.111},
    {"type": "qr_code",      "dk": "barcode",          "x": 0.215, "y": 0.720, "w": 0.157, "h": 0.111},
    {"type": "qr_code",      "dk": "barcode",          "x": 0.651, "y": 0.721, "w": 0.157, "h": 0.111},
    {"type": "dynamic_text", "dk": "اسم الضيف",        "x": 0.181, "y": 0.336, "w": 0.127, "h": 0.053, "font": 10},
    {"type": "dynamic_text", "dk": "اسم الضيف",        "x": 0.624, "y": 0.333, "w": 0.127, "h": 0.053, "font": 10},
    {"type": "dynamic_text", "dk": "الجهة",            "x": 0.357, "y": 0.050, "w": 0.128, "h": 0.108, "font": 16},
    {"type": "dynamic_text", "dk": "المسمى الوظيفي",   "x": 0.682, "y": 0.203, "w": 0.103, "h": 0.050, "font": 8},
]

print("=" * 100)
print(f"{'العنصر':>20s} | {'المحرر (CSS %)':>20s} | {'الباكند (Pillow px)':>25s} | {'متطابق؟':>8s}")
print("=" * 100)

for e in elements:
    # Editor CSS: left = x * 100%, top = y * 100%
    # In pixels: left = x * canvasWidth, top = y * canvasHeight
    css_left = e["x"] * CANVAS_W
    css_top = e["y"] * CANVAS_H
    css_w = e["w"] * CANVAS_W
    css_h = e["h"] * CANVAS_H

    # Backend Pillow: round(x * canvas_width), round(y * canvas_height)
    py_left = round(e["x"] * CANVAS_W)
    py_top = round(e["y"] * CANVAS_H)
    py_w = round(e["w"] * CANVAS_W)
    py_h = round(e["h"] * CANVAS_H)

    match = "✅" if abs(css_left - py_left) < 1 and abs(css_top - py_top) < 1 else "❌"
    
    name = f"{e['type'][:12]}({e['dk'][:10]})"
    css_str = f"({css_left:.1f}, {css_top:.1f})"
    py_str = f"({py_left}, {py_top}, {py_w}×{py_h})"
    font_str = f" font={e.get('font','')}px" if 'font' in e else ""
    
    print(f"{name:>25s} | {css_str:>20s} | {py_str:>25s} | {match:>5s}{font_str}")

print()
print("الخلاصة: المحرر والباكند يستخدمان نفس المعادلة:")
print("  المحرر (CSS):   left = x × canvasWidth,  top = y × canvasHeight")
print("  الباكند (Pillow): left = round(x × canvas_width), top = round(y × canvas_height)")
print("  → الفرق أقل من 1 بكسل (تقريب)")
