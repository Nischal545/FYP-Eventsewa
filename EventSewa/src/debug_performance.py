import os
import django
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection
from googlelogin.models import Event, Organizer
from googlelogin.event_table import EventTable

def main():
    print("=== DEBUGGING PERFORMANCE ISSUES ===")
    
    # 1. Check database connection
    print("\nTesting database connection...")
    start_time = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"Database connection successful: {result}")
    except Exception as e:
        print(f"Database connection error: {str(e)}")
    print(f"Database connection test took {time.time() - start_time:.4f} seconds")
    
    # 2. Check Event model operations
    print("\nTesting Event model operations...")
    start_time = time.time()
    try:
        # Count events
        event_count = Event.objects.count()
        print(f"Event count: {event_count}")
        
        # Generate event code
        code = Event.generate_event_code()
        print(f"Generated event code: {code}")
    except Exception as e:
        print(f"Event model error: {str(e)}")
    print(f"Event model operations took {time.time() - start_time:.4f} seconds")
    
    # 3. Check EventTable operations
    print("\nTesting EventTable operations...")
    start_time = time.time()
    try:
        # Generate table name
        table_name = EventTable.generate_table_name("Test Event", "AB1234")
        print(f"Generated table name: {table_name}")
        
        # Check if we can create and drop a test table
        create_start = time.time()
        EventTable.create_table(table_name)
        print(f"Table creation took {time.time() - create_start:.4f} seconds")
        
        drop_start = time.time()
        EventTable.drop_table(table_name)
        print(f"Table deletion took {time.time() - drop_start:.4f} seconds")
    except Exception as e:
        print(f"EventTable error: {str(e)}")
    print(f"EventTable operations took {time.time() - start_time:.4f} seconds")
    
    # 4. Check Organizer model operations
    print("\nTesting Organizer model operations...")
    start_time = time.time()
    try:
        # Count organizers
        organizer_count = Organizer.objects.count()
        print(f"Organizer count: {organizer_count}")
    except Exception as e:
        print(f"Organizer model error: {str(e)}")
    print(f"Organizer model operations took {time.time() - start_time:.4f} seconds")
    
    # 5. Check SQL queries executed
    print("\nSQL queries executed:")
    for i, query in enumerate(connection.queries):
        print(f"{i+1}. Time: {query['time']}, SQL: {query['sql'][:100]}...")

if __name__ == "__main__":
    main()
