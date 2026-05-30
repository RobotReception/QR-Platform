import urllib.request
import json
req = urllib.request.Request(
    'http://localhost:8030/api/v1/auth/password-reset/send-otp',
    data=json.dumps({"email": "eng.mo.alshebly@gmail.com"}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    print(urllib.request.urlopen(req).read())
except Exception as e:
    print(e)
    if hasattr(e, 'read'):
        print(e.read())
