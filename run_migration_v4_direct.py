"""
Execute Migration V4 using Supabase SQL endpoint directly
"""
import httpx
import re

# Configuration
SUPABASE_URL = 'https://vyzvvtyszwbefgkzgjzd.supabase.co'
SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5enZ2dHlzendiZWZna3pnanpkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTYwMzYyMywiZXhwIjoyMDg3MTc5NjIzfQ.bqRS2yebVU8E6UlBybBrkG-6Z5rFBs9pGVEPb-hJ6Hs'

def execute_sql_batch(sql):
    """Execute SQL batch via Supabase SQL endpoint."""
    url = f"{SUPABASE_URL}/rest/v1/sql"
    headers = {
        'apikey': SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
    }
    
    try:
        response = httpx.post(url, headers=headers, json={"query": sql}, timeout=60)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

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
    print("  Migration V4: Event System Improvements")
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
    
    # Execute in batches
    print("\nExecuting migration...")
    success = 0
    skipped = 0
    errors = 0
    
    # Group statements into batches
    batch_size = 10
    for i in range(0, len(statements), batch_size):
        batch = statements[i:i+batch_size]
        batch_sql = '\n'.join(batch)
        
        status_code, response = execute_sql_batch(batch_sql)
        
        if status_code == 200:
            success += len(batch)
            print(f"  Batch {i//batch_size + 1}: ✅ Executed ({len(batch)} statements)")
        elif status_code == 400 and "already exists" in response.lower():
            skipped += len(batch)
            print(f"  Batch {i//batch_size + 1}: ⏭️  Skipped (already exists)")
        else:
            errors += len(batch)
            print(f"  Batch {i//batch_size + 1}: ❌ Error ({status_code}): {response[:200]}")
    
    print("\n" + "=" * 60)
    print(f"  Summary: {success} executed, {skipped} skipped, {errors} errors")
    print("=" * 60)
    
    if errors > 0:
        print("\n⚠️  Some statements failed. Please execute via Supabase Dashboard:")
        print("   https://app.supabase.com/project/vyzvvtyszwbefgkzgjzd/sql")
        print("\nCopy the content of: supabase/migration_v4_event_improvements.sql")

if __name__ == "__main__":
    main()
