import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection

def main():
    print("=== APPROVING HERALD ORG ===")
    
    try:
        with connection.cursor() as cursor:
            # Update status to approved
            cursor.execute("""
                UPDATE users.organizer_requests 
                SET status = 'approved' 
                WHERE organization_name = 'Herald Org'
                RETURNING id, email, status
            """)
            
            result = cursor.fetchone()
            
            if result:
                print(f"Herald Org approved successfully:")
                print(f"  ID: {result[0]}")
                print(f"  Email: {result[1]}")
                print(f"  Status: {result[2]}")
            else:
                print("Herald Org not found in the database!")
                
    except Exception as e:
        print(f"Error approving account: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 