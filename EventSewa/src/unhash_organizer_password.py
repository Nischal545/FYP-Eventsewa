import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest
from django.contrib.auth.hashers import check_password

def main():
    print("=== UNHASHING ORGANIZER PASSWORD ===")
    
    # Get the organizer
    try:
        organizer = OrganizerRequest.objects.filter(status='approved').first()
        
        if not organizer:
            print("No approved organizer found!")
            return
        
        print(f"Found organizer: {organizer.email}")
        print(f"Current password hash: {organizer.password}")
        
        # The actual password we know is correct
        plain_password = 'Nischal123..'
        
        # Verify it's correct
        is_valid = check_password(plain_password, organizer.password)
        print(f"Password verification: {is_valid}")
        
        if is_valid:
            # Update the password to plain text
            organizer.password = plain_password
            organizer.save()
            print(f"Password updated to plain text: '{plain_password}'")
            print("You should now be able to log in with direct password comparison")
        else:
            print("Password verification failed! Cannot update password.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
