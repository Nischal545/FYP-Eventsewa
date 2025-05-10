import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest
from django.db.models import Q

def main():
    print("=== CHECKING ORGANIZER REQUESTS ===")
    
    # Get all organizer requests
    organizer_requests = OrganizerRequest.objects.all()
    
    if not organizer_requests:
        print("No organizer requests found in the database.")
        return
    
    print(f"Found {organizer_requests.count()} organizer requests:")
    
    for i, org in enumerate(organizer_requests, 1):
        print(f"\n{i}. Organizer Request:")
        print(f"   ID: {org.id}")
        print(f"   Email: {org.email}")
        print(f"   Username: {org.username}")
        print(f"   Organization Name: {org.organization_name}")
        print(f"   Status: {org.status}")
        print(f"   Password: {org.password}")
        print(f"   Password Length: {len(org.password) if org.password else 0}")
    
    # Try to find an approved organizer
    approved_organizers = OrganizerRequest.objects.filter(status='approved')
    
    if approved_organizers:
        print("\n=== APPROVED ORGANIZERS ===")
        for i, org in enumerate(approved_organizers, 1):
            print(f"\n{i}. Approved Organizer:")
            print(f"   ID: {org.id}")
            print(f"   Email: {org.email}")
            print(f"   Username: {org.username}")
            print(f"   Organization Name: {org.organization_name}")
            print(f"   Password: {org.password}")
            print(f"   Password Length: {len(org.password) if org.password else 0}")
    else:
        print("\nNo approved organizers found.")
        
    # Ask for a test login
    print("\n=== TEST LOGIN ===")
    email = input("Enter organizer email or username to test: ")
    password = input("Enter password to test: ")
    
    organizer = OrganizerRequest.objects.filter(
        Q(email=email) | Q(username=email),
        status='approved'
    ).first()
    
    if organizer:
        print(f"\nFound organizer: {organizer.email}")
        print(f"Stored password: '{organizer.password}'")
        print(f"Input password: '{password}'")
        
        if organizer.password == password:
            print("✅ Password match: SUCCESS")
        else:
            print("❌ Password match: FAILED")
            print("Possible issues:")
            print("1. Password is stored with hashing but compared directly")
            print("2. Password has leading/trailing whitespace")
            print("3. Password case sensitivity mismatch")
    else:
        print(f"\nNo approved organizer found with email/username: {email}")

if __name__ == "__main__":
    main()
