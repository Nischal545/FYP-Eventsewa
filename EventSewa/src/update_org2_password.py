import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.db import connection

def dictfetchone(cursor):
    """Return a dictionary from a database row"""
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, cursor.fetchone())) if cursor.rowcount > 0 else None

def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dictionaries"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def main():
    print("=== UPDATING ORGANIZATION2 PASSWORD ===")
    
    try:
        # New password to set - plain text without hashing
        new_password = "Nischal123.."
        
        # Update password in database
        with connection.cursor() as cursor:
            # First check if Organization2 exists in organizer_requests
            cursor.execute("""
                SELECT id, organization_name, username, email, status 
                FROM users.organizer_requests 
                WHERE username = 'Organization2'
            """)
            result = cursor.fetchone()
            
            if result:
                org_id = result[0]
                org_email = result[3]
                
                print(f"Found Organization2 in organizer_requests:")
                print(f"  ID: {result[0]}")
                print(f"  Organization Name: {result[1]}")
                print(f"  Username: {result[2]}")
                print(f"  Email: {result[3]}")
                print(f"  Status: {result[4]}")
                
                # Update the password in organizer_requests with plain text
                cursor.execute("""
                    UPDATE users.organizer_requests 
                    SET password = %s 
                    WHERE username = 'Organization2'
                """, [new_password])
                
                print(f"Password updated in organizer_requests table!")
                
                # Now check if Organization2 exists in organizers table by email
                cursor.execute("""
                    SELECT id, organization_name, email, password, verification_status 
                    FROM organizers 
                    WHERE email = %s
                """, [org_email])
                org_result = dictfetchone(cursor)
                
                if org_result:
                    print(f"\nFound Organization2 in organizers table:")
                    print(f"  ID: {org_result['id']}")
                    print(f"  Organization Name: {org_result['organization_name']}")
                    print(f"  Email: {org_result['email']}")
                    print(f"  Verification Status: {org_result['verification_status']}")
                    
                    # Update the password in organizers table with plain text
                    cursor.execute("""
                        UPDATE organizers 
                        SET password = %s 
                        WHERE email = %s
                    """, [new_password, org_email])
                    
                    print(f"Password updated in organizers table!")
                    
                    # Test login with the new password
                    cursor.execute("""
                        SELECT id, organization_name, email, password, verification_status 
                        FROM organizers 
                        WHERE email = %s
                    """, [org_email])
                    test_org = dictfetchone(cursor)
                    
                    if test_org and test_org['password'] == new_password:
                        print(f"\nLogin test SUCCESSFUL with new password!")
                        print(f"You can now log in with:")
                        print(f"  Email: {org_email}")
                        print(f"  Password: {new_password}")
                    else:
                        print(f"\nLogin test FAILED with new password!")
                else:
                    print("\nOrganization2 not found in organizers table.")
                    print("Creating entry in organizers table...")
                    
                    # Create entry in organizers table with plain text password
                    cursor.execute("""
                        INSERT INTO organizers (user_id, organization_name, username, owner_names, email, password, address, verification_status)
                        SELECT user_id, organization_name, username, owner_names, email, %s, address, TRUE
                        FROM users.organizer_requests
                        WHERE id = %s
                    """, [new_password, org_id])
                    
                    print("Entry created in organizers table!")
                    print(f"You can now log in with:")
                    print(f"  Email: {org_email}")
                    print(f"  Password: {new_password}")
            else:
                print("Organization2 not found in the database!")
                print("Checking for other usernames...")
                
                # List all organizer_requests to help identify the correct username
                cursor.execute("""
                    SELECT id, organization_name, username, email, status 
                    FROM users.organizer_requests
                """)
                all_requests = cursor.fetchall()
                
                if all_requests:
                    print(f"Found {len(all_requests)} organizer requests in the database:")
                    for req in all_requests:
                        print(f"  ID: {req[0]}, Org Name: {req[1]}, Username: {req[2]}, Email: {req[3]}, Status: {req[4]}")
                    
                    # Also check organizers table
                    cursor.execute("""
                        SELECT id, organization_name, email, verification_status 
                        FROM organizers
                    """)
                    all_orgs = dictfetchall(cursor)
                    
                    if all_orgs:
                        print(f"\nFound {len(all_orgs)} entries in organizers table:")
                        for org in all_orgs:
                            print(f"  ID: {org['id']}, Name: {org['organization_name']}, Email: {org['email']}, Status: {org['verification_status']}")
                    else:
                        print("\nNo entries found in organizers table!")
                else:
                    print("No organizer requests found in the database!")
                
    except Exception as e:
        print(f"Error updating password: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()