import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import UserProfile

# Update verification status for nischal123
user = UserProfile.objects.filter(username='nischal123').first()
if user:
    user.verification_status = True
    user.save()
    print(f"User {user.username} verification status updated to {user.verification_status}")
else:
    print("User not found")

# Verify the update
print("\nUpdated User List:")
print('Username | Email | Password | Verification Status')
print('-' * 80)
for user in UserProfile.objects.all():
    print(f'{user.username} | {user.email} | {user.password[:5]}... | {user.verification_status}')
