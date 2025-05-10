import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import UserProfile

# Get full password for nisha123
user = UserProfile.objects.filter(username='nisha123').first()
if user:
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Full Password: '{user.password}'")
    print(f"Password Length: {len(user.password)}")
    print(f"Verification Status: {user.verification_status}")
else:
    print("User not found")
