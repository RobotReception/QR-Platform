import urllib.request
import urllib.parse
import json
import os
import sys

# Add path info
sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://localhost:8020/api/v1"

# Prepare dummy font file content (a valid TTF file structure isn't required for upload_font if we bypass PIL check, but let's check: 
# wait! The backend upload_font endpoint checks if PIL can load it:
# ImageFont.truetype(io.BytesIO(content), 12)
# So we need to send a valid TTF file content or use a dummy file that PIL can parse, or simply copy an existing font from the fonts directory to use as our test payload!)
# Let's see if we can find an existing font in the fonts/ directory.

fonts_dir = "fonts"
existing_fonts = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))] if os.path.exists(fonts_dir) else []

if not existing_fonts:
    print("No existing fonts found in fonts/ directory to use for testing.")
    sys.exit(0)

test_font_name = existing_fonts[0]
font_path = os.path.join(fonts_dir, test_font_name)
print(f"Using existing font '{test_font_name}' for testing upload...")

with open(font_path, "rb") as f:
    font_bytes = f.read()

# Helper for multipart form-data upload
def upload_file(url, file_bytes, filename, fieldname="file"):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    data = []
    data.append(f"--{boundary}".encode('utf-8'))
    data.append(f'Content-Disposition: form-data; name="{fieldname}"; filename="{filename}"'.encode('utf-8'))
    data.append(b'Content-Type: application/octet-stream')
    data.append(b'')
    data.append(file_bytes)
    data.append(f"--{boundary}--".encode('utf-8'))
    data.append(b'')
    body = b'\r\n'.join(data)
    
    req = urllib.request.Request(url, data=body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('X-Tenant-ID', '45e2bbee-4689-44b9-b803-1ee07f22e168')
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Upload error: {e}")
        if hasattr(e, 'read'):
            print(f"Error details: {e.read().decode('utf-8')}")
        return None, None

print("\n--- 1. Testing Upload of Font with Spaces and Uppercase Extension ---")
# Upload font as 'Test Amiri Bold.TTF'
upload_url = f"{API_URL}/templates/fonts/upload"
status, response = upload_file(upload_url, font_bytes, "Test Amiri Bold.TTF")
print(f"Upload Status: {status}")
print(f"Upload Response: {response}")

if not response or response.get("status") != "success":
    print("Upload failed. Stopping test.")
    sys.exit(1)

family_name = response.get("font_family")
print(f"Font successfully saved in backend with family name: {family_name}")

# Now let's verify if the file was saved as TestAmiriBold.ttf
expected_filename = f"{family_name}.ttf"
saved_path = os.path.join("fonts", expected_filename)
print(f"Checking disk for file '{saved_path}': {'Found' if os.path.exists(saved_path) else 'Not Found'}")

print("\n--- 2. Testing Font Retrieval via get_font_file ---")

# Try retrieving with original name 'Test Amiri Bold.ttf'
retrieve_url = f"{API_URL}/templates/fonts/file/{urllib.parse.quote('Test Amiri Bold.ttf')}"
print(f"Requesting retrieved font (with spaces): {retrieve_url}")
try:
    with urllib.request.urlopen(retrieve_url) as res:
        print(f"Retrieval (with spaces) status: {res.status}")
        print(f"Content-Type returned: {res.headers.get('Content-Type')}")
except Exception as e:
    print(f"Retrieval failed: {e}")

# Try retrieving with case mismatch 'testamiribold.TTF'
retrieve_url_case = f"{API_URL}/templates/fonts/file/{urllib.parse.quote('testamiribold.TTF')}"
print(f"Requesting retrieved font (case/extension mismatch): {retrieve_url_case}")
try:
    with urllib.request.urlopen(retrieve_url_case) as res:
        print(f"Retrieval (case mismatch) status: {res.status}")
        print(f"Content-Type returned: {res.headers.get('Content-Type')}")
except Exception as e:
    print(f"Retrieval failed: {e}")

# Cleanup
if os.path.exists(saved_path):
    os.remove(saved_path)
    print(f"\nCleaned up test file: {saved_path}")
