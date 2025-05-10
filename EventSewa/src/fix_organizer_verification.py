import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest, UserProfile
from django.db.models import Q

def main():
    print("=== FIXING ORGANIZER VERIFICATION ===")
    
    # Get the approved organizer
    try:
        organizer = OrganizerRequest.objects.filter(status='approved').first()
        
        if not organizer:
            print("No approved organizer found!")
            return
        
        print(f"Found organizer: {organizer.email}, status: {organizer.status}")
        
        # Find the matching user profile
        user = UserProfile.objects.filter(email=organizer.email).first()
        
        if user:
            print(f"Found matching user: {user.username}, verification status: {user.verification_status}")
            
            # Update the user verification status
            if not user.verification_status:
                user.verification_status = True
                user.save()
                print(f"Updated user verification status to True")
            else:
                print("User already verified")
        else:
            print(f"No matching user found for email: {organizer.email}")
            
            # Create a user profile if needed
            print("Creating a new user profile for the organizer...")
            new_user = UserProfile(
                name=organizer.owner_names,
                username=organizer.username,
                email=organizer.email,
                password=organizer.password,
                address=organizer.address,
                phone_number=organizer.phone,
                verification_status=True
            )
            new_user.save()
            print(f"Created new user profile with username: {new_user.username}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
