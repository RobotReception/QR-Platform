"""
Execute Migration V4 on Local Supabase
"""
import psycopg2
import re

# Local Supabase connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5434,
    "user": "postgres",
    "password": "postgres",
    "dbname": "postgres",
    "sslmode": "disable",
}

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
    print("  Migration V4: Event System Improvements (Local)")
    print("=" * 60)
    
    # Connect to local database
    print("\nConnecting to local Supabase database...")
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=15)
        conn.autocommit = True
        print("✅ Connected to local database")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Read migration file
    print("\nReading migration file...")
    with open('supabase/migration_v4_event_improvements.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(f"SQL file size: {len(sql_content)} characters")
    
    # Split and execute
    print("\nExecuting migration...")
    statements = split_sql_statements(sql_content)
    print(f"Found {len(statements)} SQL statements")
    
    cur = conn.cursor()
    success = 0
    skipped = 0
    errors = 0
    
    for i, stmt in enumerate(statements, 1):
        stmt = stmt.strip()
        if not stmt or stmt.startswith('--'):
            continue
        
        try:
            cur.execute(stmt)
            success += 1
            print(f"  [{i}/{len(statements)}] ✅ Executed")
        except Exception as e:
            error_msg = str(e).strip()
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                skipped += 1
                print(f"  [{i}/{len(statements)}] ⏭️  Skipped (already exists)")
            else:
                errors += 1
                print(f"  [{i}/{len(statements)}] ❌ Error: {error_msg[:100]}")
    
    print("\n" + "=" * 60)
    print(f"  Summary: {success} executed, {skipped} skipped, {errors} errors")
    print("=" * 60)
    
    conn.close()
    return errors == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
