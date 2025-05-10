import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import UserProfile

print('Username | Email | Password | Verification Status')
print('-' * 80)
for user in UserProfile.objects.all():
    print(f'{user.username} | {user.email} | {user.password[:5]}... | {user.verification_status}')
