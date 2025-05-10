import os
import django
import sys
import base64

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.EventSewa.settings')
django.setup()

from googlelogin.models import Event, Organizer
from django.db import connection

def check_events():
    print("=== Checking Events in Database ===")
    
    # Check all events
    events = Event.objects.all()
    print(f"Total events found: {len(events)}")
    
    # Print event details
    for event in events:
        print(f"Event ID: {event.id}")
        print(f"Name: {event.name}")
        print(f"Active: {event.is_active}")
        print(f"Date: {event.date}")
        print(f"Location: {event.location}")
        print(f"Price: {event.price}")
        print(f"Capacity: {event.capacity}")
        
        # Check organizer
        try:
            print(f"Organizer: {event.organizer.organization_name} (ID: {event.organizer.id})")
        except Exception as e:
            print(f"Error getting organizer: {str(e)}")
        
        # Check if event ticket table exists
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'events' AND table_name = 'event_{event.id}_tickets')")
                table_exists = cursor.fetchone()[0]
                print(f"Ticket table exists: {table_exists}")
                
                if table_exists:
                    cursor.execute(f"SELECT COUNT(*) FROM events.event_{event.id}_tickets")
                    ticket_count = cursor.fetchone()[0]
                    print(f"Ticket count: {ticket_count}")
        except Exception as e:
            print(f"Error checking ticket table: {str(e)}")
            
        print("-" * 50)

if __name__ == "__main__":
    check_events()
