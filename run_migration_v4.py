"""
Execute Migration V4: Event System Improvements
"""
import psycopg2
import re
import getpass

# Configuration
SUPABASE_URL = 'https://vyzvvtyszwbefgkzgjzd.supabase.co'
PROJECT_REF = 'vyzvvtyszwbefgkzgjzd'

def get_db_connection(password):
    """Connect to Supabase Cloud PostgreSQL."""
    connection_configs = [
        {
            "name": "Direct connection",
            "host": f"db.{PROJECT_REF}.supabase.co",
            "port": 5432,
            "user": "postgres",
            "password": password,
            "dbname": "postgres",
            "sslmode": "require",
        },
        {
            "name": "Connection Pooler (Transaction)",
            "host": "aws-0-eu-central-1.pooler.supabase.com",
            "port": 6543,
            "user": f"postgres.{PROJECT_REF}",
            "password": password,
            "dbname": "postgres",
            "sslmode": "require",
        },
    ]
    
    for config in connection_configs:
        name = config.pop("name")
        try:
            print(f"Trying {name}...", end=" ")
            conn = psycopg2.connect(**config, connect_timeout=15)
            conn.autocommit = True
            print("✅ Connected!")
            return conn
        except Exception as e:
            print(f"❌ {str(e)[:80]}")
            config["name"] = name
    
    return None

def split_sql_statements(sql_content):
    """Split SQL content into individual statements."""
    statements = []
    current = []
    in_dollar = False
    dollar_tag = None
    
    for line in sql_content.split('\n'):
        # Handle $$ string literals
        if '$$' in line:
            if not in_dollar:
                in_dollar = True
                dollar_tag = '$$'
            else:
                in_dollar = False
                dollar_tag = None
            current.append(line)
            continue
        
        if in_dollar:
            current.append(line)
            continue
        
        # Split on semicolon
        if ';' in line:
            parts = line.split(';', 1)
            current.append(parts[0])
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt + ';')
            current = [parts[1]] if len(parts) > 1 else []
        else:
            current.append(line)
    
    # Add remaining
    stmt = '\n'.join(current).strip()
    if stmt and not stmt.startswith('--'):
        statements.append(stmt)
    
    return statements

def execute_migration():
    """Execute migration V4."""
    print("=" * 60)
    print("  Migration V4: Event System Improvements")
    print("=" * 60)
    
    # Get password
    password = getpass.getpass("Enter Supabase database password: ")
    
    # Connect
    print("\nConnecting to database...")
    conn = get_db_connection(password)
    if not conn:
        print("❌ Failed to connect to database")
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
    execute_migration()
