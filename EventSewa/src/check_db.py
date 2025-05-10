import psycopg2
from src.settings import DATABASES

# Get database configuration
db_config = DATABASES['default']

try:
    # Connect to the database
    conn = psycopg2.connect(
        dbname=db_config['NAME'],
        user=db_config['USER'],
        password=db_config['PASSWORD'],
        host=db_config['HOST'],
        port=db_config['PORT']
    )
    
    # Create a cursor
    cur = conn.cursor()
    
    # Query to get table structure
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'users' AND table_name = 'admins'
        ORDER BY ordinal_position;
    """)
    
    # Print the results
    print("Columns in users.admins table:")
    for row in cur.fetchall():
        print(f"Column: {row[0]}, Type: {row[1]}, Max Length: {row[2]}")
    
    # Close the cursor and connection
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}") 