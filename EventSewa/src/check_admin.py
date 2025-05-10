import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import Admin

# Check for admin accounts
admins = Admin.objects.all()
print(f"Found {len(admins)} admin accounts:")
for admin in admins:
    print(f"Username: {admin.username}")
    print(f"Email: {admin.email}")
    print(f"Password: {admin.password}")
    print(f"Type: {admin.type}")
    print("-" * 30)

# If no admin accounts exist, create one
if not admins:
    print("Creating admin account...")
    admin = Admin(
        name="Administrator",
        email="admin@example.com",
        username="admin",
        password="admin123",
        type="super_admin"
    )
    admin.save()
    print("Admin account created successfully!")
    print(f"Username: {admin.username}")
    print(f"Password: {admin.password}")
