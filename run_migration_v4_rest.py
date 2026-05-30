"""
Execute Migration V4 using Supabase REST API
"""
import httpx
import json

# Configuration
SUPABASE_URL = 'https://vyzvvtyszwbefgkzgjzd.supabase.co'
SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5enZ2dHlzendiZWZna3pnanpkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTYwMzYyMywiZXhwIjoyMDg3MTc5NjIzfQ.bqRS2yebVU8E6UlBybBrkG-6Z5rFBs9pGVEPb-hJ6Hs'

def execute_sql_via_rest(sql):
    """Execute SQL via Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        'apikey': SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    # Try using exec_sql function if it exists
    try:
        response = httpx.post(url, headers=headers, json={"query": sql}, timeout=30)
        if response.status_code == 200:
            return True, "Executed successfully"
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def split_sql_statements(sql_content):
    """Split SQL content into individual statements."""
    statements = []
    current = []
    in_dollar = False
    
    for line in sql_content.split('\n'):
        if '$$' in line:
            in_dollar = not in_dollar
            current.append(line)
            continue
        
        if in_dollar:
            current.append(line)
            continue
        
        if ';' in line:
            parts = line.split(';', 1)
            current.append(parts[0])
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt + ';')
            current = [parts[1]] if len(parts) > 1 else []
        else:
            current.append(line)
    
    stmt = '\n'.join(current).strip()
    if stmt and not stmt.startswith('--'):
        statements.append(stmt)
    
    return statements

def main():
    print("=" * 60)
    print("  Migration V4: Event System Improvements (REST API)")
    print("=" * 60)
    
    # Read migration file
    print("\nReading migration file...")
    with open('supabase/migration_v4_event_improvements.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(f"SQL file size: {len(sql_content)} characters")
    
    # Split statements
    print("\nSplitting SQL statements...")
    statements = split_sql_statements(sql_content)
    print(f"Found {len(statements)} SQL statements")
    
    # Execute via Supabase Dashboard SQL Editor recommendation
    print("\n" + "=" * 60)
    print("  ⚠️  IMPORTANT: Please execute via Supabase Dashboard")
    print("=" * 60)
    print("\nDue to REST API limitations, please:")
    print("1. Open Supabase Dashboard: https://app.supabase.com")
    print("2. Go to SQL Editor")
    print("3. Copy the content of: supabase/migration_v4_event_improvements.sql")
    print("4. Paste and execute")
    print("\nThis is the safest method for schema changes.")
    
    # Save to clipboard if possible
    try:
        import pyperclip
        pyperclip.copy(sql_content)
        print("\n✅ SQL content copied to clipboard!")
    except:
        print("\n💡 Tip: Install pyperclip to auto-copy: pip install pyperclip")

if __name__ == "__main__":
    main()
