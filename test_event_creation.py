import json, urllib.request, urllib.error, sys, random
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8020/api/v1'

# First, try to signup
rand_num = random.randint(1000, 9999)
signup_data = {
    'email': f'test_event_{rand_num}@example.com',
    'password': 'Test123456!',
    'full_name': 'Test User',
    'organization_name': 'Test Org'
}

req = urllib.request.Request(BASE + '/auth/signup',
                           data=json.dumps(signup_data).encode(),
                           headers={'Content-Type': 'application/json'},
                           method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        signup_result = json.loads(resp.read().decode())
        print('Signup successful')
        tenant_data = signup_result.get('tenants', [{}])[0]
        tenant_id = tenant_data.get('tenant_id')
        user_id = signup_result.get('user_id')
        print(f'Tenant ID: {tenant_id}')
        print(f'User ID: {user_id}')
        
        # Now login to get access token
        login_data = {
            'email': signup_data['email'],
            'password': signup_data['password']
        }
        
        login_req = urllib.request.Request(BASE + '/auth/login',
                                          data=json.dumps(login_data).encode(),
                                          headers={'Content-Type': 'application/json'},
                                          method='POST')
        try:
            with urllib.request.urlopen(login_req) as login_resp:
                login_result = json.loads(login_resp.read().decode())
                access_token = login_result.get('access_token')
                print('Login successful')
                
                if tenant_id and access_token:
                    # Now try to create an event
                    event_data = {
                        'title': 'Test Event',
                        'start_date': '2026-04-05T10:00:00Z',
                        'timezone': 'Asia/Riyadh'
                    }
                    
                    req = urllib.request.Request(BASE + '/events',
                                               data=json.dumps(event_data).encode(),
                                               headers={
                                                   'Content-Type': 'application/json',
                                                   'Authorization': f'Bearer {access_token}',
                                                   'X-Tenant-ID': tenant_id
                                               },
                                               method='POST')
                    try:
                        with urllib.request.urlopen(req) as resp:
                            event_result = json.loads(resp.read().decode())
                            print('Event created successfully')
                            print(f'Event ID: {event_result.get("id")}')
                    except urllib.error.HTTPError as e:
                        body = e.read().decode()
                        print(f'Event creation failed: {e.code}')
                        print(f'Error: {body}')
                else:
                    print('Missing tenant_id or access_token')
                    
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f'Login failed: {e.code}')
            print(f'Error: {body}')
        
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'Signup failed: {e.code}')
    print(f'Error: {body}')