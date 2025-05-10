import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.utils import timezone
from googlelogin.models import Event, UserProfile, OrganizerRequest, Organizer

def debug_organizer_dashboard():
    try:
        print("=== DEBUGGING ORGANIZER DASHBOARD ===")
        
        # Test organizer retrieval
        print("\nTesting organizer retrieval...")
        
        # Get all organizer requests
        organizer_requests = OrganizerRequest.objects.all()
        print(f"Total organizer requests: {organizer_requests.count()}")
        for i, org_req in enumerate(organizer_requests):
            print(f"{i+1}. ID: {org_req.id}, Name: {org_req.organization_name}, Email: {org_req.email}")
        
        # Get all organizers
        organizers = Organizer.objects.all()
        print(f"\nTotal organizers: {organizers.count()}")
        for i, org in enumerate(organizers):
            print(f"{i+1}. ID: {org.id}, Name: {org.organization_name}, Email: {org.email}")
        
        # Test event retrieval
        print("\nTesting event retrieval...")
        events = Event.objects.all()
        print(f"Total events: {events.count()}")
        
        for i, event in enumerate(events):
            print(f"\nEvent {i+1}:")
            print(f"  ID: {event.id}")
            print(f"  Name: {event.name}")
            print(f"  Code: {event.event_code}")
            print(f"  Organizer ID: {event.organizer_id}")
            
            # Test if we can access the organizer
            try:
                organizer = event.organizer
                print(f"  Organizer Name: {organizer.organization_name}")
            except Exception as e:
                print(f"  Error accessing organizer: {str(e)}")
            
            # Test image processing
            try:
                if event.image:
                    import base64
                    if isinstance(event.image, bytes) and len(event.image) > 0:
                        image_base64 = base64.b64encode(event.image).decode('utf-8')
                        print(f"  Image: Successfully processed ({len(image_base64)} chars)")
                    else:
                        print(f"  Image: Invalid format - {type(event.image)}")
                else:
                    print("  Image: None")
            except Exception as img_error:
                print(f"  Error processing image: {str(img_error)}")
        
        # Test dashboard view logic
        print("\nSimulating dashboard view logic...")
        
        # Pick the first organizer request for testing
        if organizer_requests.exists():
            organizer_id = organizer_requests.first().id
            print(f"Using organizer_id: {organizer_id}")
            
            try:
                # Try to find the organizer in the OrganizerRequest table first
                organizer_request = OrganizerRequest.objects.get(id=organizer_id)
                print(f"Found organizer request: {organizer_request.email}")
                organizer_data = organizer_request
                
                # Try to find events for this organizer
                try:
                    # First, check if there's an Organizer record for this organizer request
                    organizer_obj = Organizer.objects.get(user_id=organizer_request.user_id)
                    print(f"Found matching Organizer record: {organizer_obj.email}")
                    
                    # Get events for this organizer
                    events = Event.objects.filter(organizer=organizer_obj).order_by('-created_at')
                    print(f"Found {events.count()} events for organizer")
                except Organizer.DoesNotExist:
                    print("No matching Organizer record found")
                    # Try to find events by organizer_request_id (legacy data)
                    events = Event.objects.filter(organizer_request_id=organizer_id).order_by('-created_at')
                    print(f"Found {events.count()} events by organizer_request_id")
                
                # Process events for display
                upcoming_events = []
                past_events = []
                
                current_time = timezone.now()
                for event in events:
                    # Calculate financial information
                    event.gross_revenue = float(event.price) * event.capacity
                    event.event_fee = event.gross_revenue * 0.1  # 10% fee
                    event.net_revenue = event.gross_revenue - event.event_fee
                    
                    # Categorize events
                    if event.date > current_time:
                        upcoming_events.append(event)
                    else:
                        past_events.append(event)
                
                print(f"Upcoming events: {len(upcoming_events)}")
                print(f"Past events: {len(past_events)}")
                print("Dashboard view logic simulation successful!")
                
            except OrganizerRequest.DoesNotExist:
                print(f"No organizer request found with ID: {organizer_id}")
                
            except Exception as e:
                print(f"Error in dashboard logic: {str(e)}")
                traceback.print_exc()
        else:
            print("No organizer requests found for testing")
        
    except Exception as e:
        print(f"Error in debug_organizer_dashboard: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_organizer_dashboard()
