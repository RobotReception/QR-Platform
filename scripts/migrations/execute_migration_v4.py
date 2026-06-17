"""
Execute Migration V4 using Supabase Python Client
"""
import os
from supabase import create_client
import re

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54821")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

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
    
    # Connect to Supabase
    print("\nConnecting to Supabase...")
    client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
    print("✅ Connected")
    
    # Try to execute via RPC if exec_sql function exists
    print("\nAttempting to execute via RPC...")
    success = 0
    skipped = 0
    errors = 0
    
    for i, stmt in enumerate(statements, 1):
        stmt = stmt.strip()
        if not stmt or stmt.startswith('--'):
            continue
        
        try:
            # Try RPC call
            result = client.rpc('exec_sql', params={'query': stmt}).execute()
            success += 1
            print(f"  [{i}/{len(statements)}] ✅ Executed")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                skipped += 1
                print(f"  [{i}/{len(statements)}] ⏭️  Skipped (already exists)")
            else:
                errors += 1
                print(f"  [{i}/{len(statements)}] ❌ Error: {error_msg[:100]}")
    
    print("\n" + "=" * 60)
    print(f"  Summary: {success} executed, {skipped} skipped, {errors} errors")
    print("=" * 60)
    
    if errors > 0 or success == 0:
        print("\n⚠️  RPC method failed. Please execute via Supabase Dashboard:")
        print("   https://app.supabase.com/project/vyzvvtyszwbefgkzgjzd/sql")
        print("\nCopy the content of: supabase/migration_v4_event_improvements.sql")

if __name__ == "__main__":
    main()
