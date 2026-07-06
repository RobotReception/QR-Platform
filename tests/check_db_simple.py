import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5434,
    user='postgres',
    password='postgres',
    dbname='postgres',
    sslmode='disable'
)
conn.autocommit = True
cur = conn.cursor()

# Check tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
tables = [row[0] for row in cur.fetchall()]
print('Tables in database:', tables)

# Check if events table has columns
if 'events' in tables:
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'events'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    print('\nEvents table columns:')
    for col in columns:
        print(f'  {col[0]} ({col[1]})')

conn.close()
