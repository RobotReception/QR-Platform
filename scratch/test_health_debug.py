import sys
import os
sys.path.insert(0, os.path.abspath("."))

import uvicorn
import threading
import urllib.request
import time
import traceback

# Import the app to ensure there are no import-time errors
from app.main import app

def run_server():
    try:
        uvicorn.run(app, host="127.0.0.1", port=8029, log_level="debug")
    except Exception as e:
        print(f"Server exception: {e}")
        traceback.print_exc()

# Start server in a background thread
t = threading.Thread(target=run_server, daemon=True)
t.start()

# Wait for server to start
time.sleep(2)

# Make a request to health check
url = "http://127.0.0.1:8029/health"
print(f"Requesting: {url}")
try:
    with urllib.request.urlopen(url) as res:
        print(f"Response Status: {res.status}")
        print(f"Response Body: {res.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    print(f"Error Body: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Request exception: {e}")
    traceback.print_exc()

print("Stopping test.")
sys.exit(0)
