import sys
import os
sys.path.insert(0, os.path.abspath("."))

import uvicorn
import threading
import urllib.request
import urllib.parse
import json
import time
import traceback

from app.main import app

def run_server():
    try:
        uvicorn.run(app, host="127.0.0.1", port=8029, log_level="warning")
    except Exception as e:
        print(f"Server exception: {e}")

# Start server in a background thread
t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(2)  # Wait for server to bind

API_URL = "http://127.0.0.1:8029/api/v1"
fonts_dir = "fonts"
existing_fonts = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))] if os.path.exists(fonts_dir) else []

if not existing_fonts:
    print("CRITICAL: No fonts found in fonts/ directory to run test.")
    sys.exit(1)

test_font_name = existing_fonts[0]
font_path = os.path.join(fonts_dir, test_font_name)
print(f"Using existing font '{test_font_name}' for testing upload...")

with open(font_path, "rb") as f:
    font_bytes = f.read()

# Helper for multipart form-data upload with tenant headers
def upload_file(url, file_bytes, filename, tenant_id, fieldname="file"):
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
    req.add_header('X-Tenant-ID', tenant_id)
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
tenant_id = "45e2bbee-4689-44b9-b803-1ee07f22e168"
status, response = upload_file(upload_url, font_bytes, "Test Amiri Bold.TTF", tenant_id)
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

# Try retrieving with original name 'Test Amiri Bold.ttf' (which has space)
retrieve_url = f"{API_URL}/templates/fonts/file/{urllib.parse.quote('Test Amiri Bold.ttf')}"
print(f"Requesting: {retrieve_url}")
try:
    with urllib.request.urlopen(retrieve_url) as res:
        print(f"Retrieval (with spaces) status: {res.status}")
        print(f"Content-Type returned: {res.headers.get('Content-Type')}")
except Exception as e:
    print(f"Retrieval failed: {e}")

# Try retrieving with case mismatch 'testamiribold.TTF'
retrieve_url_case = f"{API_URL}/templates/fonts/file/{urllib.parse.quote('testamiribold.TTF')}"
print(f"Requesting: {retrieve_url_case}")
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

print("\nStandalone verification complete.")
sys.exit(0)
