# Arabic Fonts for Invitation Rendering

Place Arabic-compatible `.ttf` font files here for the render service.

## Required Fonts

| File | Font | Download |
|------|------|----------|
| `Cairo-Regular.ttf` | Cairo Regular | [Google Fonts](https://fonts.google.com/specimen/Cairo) |
| `Cairo-Bold.ttf` | Cairo Bold | Same link |
| `Tajawal-Regular.ttf` | Tajawal Regular | [Google Fonts](https://fonts.google.com/specimen/Tajawal) |
| `Tajawal-Bold.ttf` | Tajawal Bold | Same link |
| `Amiri-Regular.ttf` | Amiri Regular | [Google Fonts](https://fonts.google.com/specimen/Amiri) |

## Quick Setup

```bash
# Download Cairo font family
curl -L -o cairo.zip "https://fonts.google.com/download?family=Cairo"
unzip cairo.zip -d cairo_temp
cp cairo_temp/static/Cairo-Regular.ttf ./Cairo-Regular.ttf
cp cairo_temp/static/Cairo-Bold.ttf ./Cairo-Bold.ttf
rm -rf cairo_temp cairo.zip

# Download Tajawal
curl -L -o tajawal.zip "https://fonts.google.com/download?family=Tajawal"
unzip tajawal.zip -d tajawal_temp
cp tajawal_temp/static/Tajawal-Regular.ttf ./Tajawal-Regular.ttf
cp tajawal_temp/static/Tajawal-Bold.ttf ./Tajawal-Bold.ttf
rm -rf tajawal_temp tajawal.zip
```

## Fallback

If fonts are not found, the render service falls back to `arial.ttf` (system font) or PIL default.
Arabic text will still be reshaped correctly but may not look as polished.
