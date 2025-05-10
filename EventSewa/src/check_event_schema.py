import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection
from googlelogin.models import Event
from googlelogin.event_table import EventTable

def main():
    print("=== CHECKING EVENT SCHEMA ===")
    
    # Check if any events exist
    events = Event.objects.all()
    print(f"Total events in database: {events.count()}")
    
    if events.count() > 0:
        # Get the most recent event
        latest_event = events.order_by('-created_at').first()
        print(f"\nLatest event: {latest_event.name}")
        print(f"Event code: {latest_event.event_code}")
        
        # Generate the expected table name
        if latest_event.event_code:
            table_name = EventTable.generate_table_name(latest_event.name, latest_event.event_code)
            print(f"Expected table name: {table_name}")
            
            # Check if the table exists
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, [table_name])
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    print(f"✅ Table '{table_name}' exists!")
                    
                    # Show table structure
                    cursor.execute("""
                        SELECT column_name, data_type, character_maximum_length
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position;
                    """, [table_name])
                    columns = cursor.fetchall()
                    
                    print("\nTable structure:")
                    print("-" * 60)
                    print(f"{'Column Name':<20} {'Data Type':<15} {'Max Length':<10}")
                    print("-" * 60)
                    for col in columns:
                        col_name, data_type, max_length = col
                        max_length_str = str(max_length) if max_length is not None else "N/A"
                        print(f"{col_name:<20} {data_type:<15} {max_length_str:<10}")
                else:
                    print(f"❌ Table '{table_name}' does not exist!")
        else:
            print("Event doesn't have an event code.")
    else:
        print("No events found in the database.")
    
    print("\n=== HOW TO CHECK IN PSQL TERMINAL ===")
    print("1. Open a terminal/command prompt")
    print("2. Connect to your PostgreSQL database:")
    print("   psql -U your_username -d your_database_name")
    print("3. List all tables:")
    print("   \\dt")
    print("4. Check a specific table structure:")
    print("   \\d table_name")
    print("5. Query data from a table:")
    print("   SELECT * FROM table_name;")
    
    # List all tables in the database
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        all_tables = cursor.fetchall()
        
        print("\nAll tables in database:")
        print("-" * 40)
        for table in all_tables:
            print(table[0])

if __name__ == "__main__":
    main()
