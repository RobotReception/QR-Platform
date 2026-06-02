import httpx
import json

def test():
    # Login or get bypass info? Since we run on local system, we can authenticate or check how auth works.
    # Let's inspect the tenant id or auth endpoints.
    # Let's see if we can perform a call. We need a token.
    # Let's read auth-data.json or similar files to get credentials.
    try:
        with open('auth-data.json', 'r') as f:
            auth_data = json.load(f)
            token = auth_data.get('access_token')
            tenant_id = auth_data.get('tenant_id')
    except Exception as e:
        print("Could not load auth-data.json:", e)
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id
    }
    
    # We saw template ID 906fcad3-4765-48f6-b1d3-dcaa9919790e exists in check_tmpl.py output
    template_id = "906fcad3-4765-48f6-b1d3-dcaa9919790e"
    url = f"http://localhost:8020/api/v1/templates/{template_id}/assets?asset_type=logo"
    
    files = {
        "file": ("logo.png", b"fake png content", "image/png")
    }
    
    print("Uploading to url:", url)
    resp = httpx.post(url, headers=headers, files=files)
    print("Response status:", resp.status_code)
    print("Response body:", resp.text)

if __name__ == "__main__":
    test()
