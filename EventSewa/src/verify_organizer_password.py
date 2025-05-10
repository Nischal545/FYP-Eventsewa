import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest
from django.contrib.auth.hashers import check_password

def main():
    print("=== VERIFYING ORGANIZER PASSWORD ===")
    
    # Get the organizer
    try:
        organizer = OrganizerRequest.objects.filter(status='approved').first()
        
        if not organizer:
            print("No approved organizer found!")
            return
        
        print(f"Found organizer: {organizer.email}")
        print(f"Password hash: {organizer.password}")
        
        # Test the password
        test_password = 'Nischal123..'
        is_valid = check_password(test_password, organizer.password)
        
        print(f"Testing password: '{test_password}'")
        print(f"Password valid: {is_valid}")
        
        if not is_valid:
            print("Password verification failed! Let's try some variations:")
            
            variations = [
                'Nischal123..',
                'nischal123..',
                'Nischal123',
                'nischal123',
                'Nischal123...',
                'nischal123...',
                'Nischal123.',
                'nischal123.'
            ]
            
            for variation in variations:
                is_valid = check_password(variation, organizer.password)
                print(f"Testing '{variation}': {is_valid}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
