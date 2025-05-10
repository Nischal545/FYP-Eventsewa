import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest, UserProfile
from django.db.models import Q

def main():
    print("=== FIXING ORGANIZER STATUS ===")
    
    # Get all organizer requests
    all_requests = OrganizerRequest.objects.all()
    print(f"Total organizer requests: {all_requests.count()}")
    
    # Check status counts
    pending_count = all_requests.filter(status='pending').count()
    approved_count = all_requests.filter(status='approved').count()
    rejected_count = all_requests.filter(status='rejected').count()
    
    print(f"Status counts:")
    print(f"  Pending: {pending_count}")
    print(f"  Approved: {approved_count}")
    print(f"  Rejected: {rejected_count}")
    
    # Show all requests
    print("\nAll organizer requests:")
    for req in all_requests:
        print(f"ID: {req.id}, Email: {req.email}, Status: {req.status}, Created: {req.created_at}")
        
        # Check if this email exists in UserProfile
        user = UserProfile.objects.filter(email=req.email).first()
        if user:
            print(f"  Matching user found: {user.username}, Verified: {user.verification_status}")
        else:
            print("  No matching user found in UserProfile")
    
    # Fix the issue - ensure the organizer with username 'organization' is approved
    try:
        organizer = OrganizerRequest.objects.get(username='organization')
        old_status = organizer.status
        
        if old_status != 'approved':
            organizer.status = 'approved'
            organizer.save()
            print(f"\nFixed organizer status: {old_status} -> approved")
        else:
            print(f"\nOrganizer already has correct status: {old_status}")
    except OrganizerRequest.DoesNotExist:
        print("\nNo organizer found with username 'organization'")
    except Exception as e:
        print(f"\nError fixing organizer status: {str(e)}")

if __name__ == "__main__":
    main()
