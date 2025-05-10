import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection

def main():
    print("=== UPDATING HERALD ORG PASSWORD ===")
    
    try:
        with connection.cursor() as cursor:
            # Update password to a known value and set status to approved
            cursor.execute("""
                UPDATE users.organizer_requests 
                SET password = 'Herald123..', 
                    status = 'approved' 
                WHERE organization_name = 'Herald Org'
                RETURNING id, email, status
            """)
            
            result = cursor.fetchone()
            
            if result:
                print(f"Herald Org updated successfully:")
                print(f"  ID: {result[0]}")
                print(f"  Email: {result[1]}")
                print(f"  Status: {result[2]}")
                print("  New Password: Herald123..")
            else:
                print("Herald Org not found in the database!")
                
    except Exception as e:
        print(f"Error updating account: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 