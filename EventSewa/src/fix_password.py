import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection

def main():
    print("=== UPDATING ORGANIZATION2 PASSWORD ===")
    
    try:
        # Set the password directly without hashing
        password = "Nischal123.."
        
        with connection.cursor() as cursor:
            # Update password in organizer_requests table
            cursor.execute("""
                UPDATE users.organizer_requests 
                SET password = %s 
                WHERE username = 'Organization2'
            """, [password])
            
            print("Password updated in organizer_requests table")
            
            # Update password in organizers table
            cursor.execute("""
                UPDATE organizers 
                SET password = %s 
                WHERE email = 'nischalnov@gmail.com'
            """, [password])
            
            print("Password updated in organizers table")
            
            print(f"\nPassword has been set to: {password}")
            print("You can now log in with:")
            print("  Email: nischalnov@gmail.com")
            print(f"  Password: {password}")
            
    except Exception as e:
        print(f"Error updating password: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
