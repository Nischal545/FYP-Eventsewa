import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest
from django.db.models import Q
from django.urls import reverse

def main():
    print("=== DEBUGGING ORGANIZER DASHBOARD REDIRECT ===")
    
    # Get all organizer requests
    organizer_requests = OrganizerRequest.objects.filter(status='approved')
    
    if not organizer_requests:
        print("No approved organizer requests found in the database.")
        return
    
    organizer = organizer_requests.first()
    print(f"Found organizer: {organizer.email}, status: {organizer.status}")
    
    # Print the organizer dashboard URL
    try:
        dashboard_url = reverse('organizer:dashboard')
        print(f"Organizer dashboard URL: {dashboard_url}")
    except Exception as e:
        print(f"Error getting dashboard URL: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check if the organizer dashboard view exists
    try:
        from organizer.views import organizer_dashboard
        print("Organizer dashboard view exists")
        
        # Check the view function
        import inspect
        print("Organizer dashboard view source:")
        print(inspect.getsource(organizer_dashboard))
    except Exception as e:
        print(f"Error checking organizer dashboard view: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
