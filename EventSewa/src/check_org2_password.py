import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection

def main():
    print("=== CHECKING ORGANIZATION2 PASSWORD ===")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT organization_name, email, password, status 
                FROM users.organizer_requests 
                WHERE organization_name = 'Organization2'
            """)
            result = cursor.fetchone()
            
            if result:
                print(f"Found Organization2:")
                print(f"  Organization: {result[0]}")
                print(f"  Email: {result[1]}")
                print(f"  Password: {result[2]}")
                print(f"  Status: {result[3]}")
            else:
                print("Organization2 not found in the database!")
                
    except Exception as e:
        print(f"Error checking password: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 