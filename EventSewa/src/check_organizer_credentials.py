import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest, UserProfile
from django.db.models import Q

def main():
    print("=== CHECKING ORGANIZER CREDENTIALS ===")
    
    # Check for organizer with username 'organization'
    try:
        organizer = OrganizerRequest.objects.filter(username='organization').first()
        
        if organizer:
            print(f"Found organizer with username 'organization':")
            print(f"  ID: {organizer.id}")
            print(f"  Email: {organizer.email}")
            print(f"  Status: {organizer.status}")
            print(f"  Password: {organizer.password}")
        else:
            print("No organizer found with username 'organization'")
            
            # List all organizers
            print("\nAll organizers in the system:")
            for org in OrganizerRequest.objects.all():
                print(f"  ID: {org.id}, Username: {org.username}, Email: {org.email}, Status: {org.status}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
