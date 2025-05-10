import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from googlelogin.models import OrganizerRequest
from django.urls import reverse, resolve
from django.urls.exceptions import NoReverseMatch

def main():
    print("=== FIXING ORGANIZER LOGIN REDIRECT ===")
    
    # Check if the organizer:dashboard URL pattern exists
    try:
        dashboard_url = reverse('organizer:dashboard')
        print(f"Organizer dashboard URL exists: {dashboard_url}")
    except NoReverseMatch:
        print("ERROR: 'organizer:dashboard' URL pattern does not exist!")
        
        # Check all available URL patterns
        from django.urls import get_resolver
        resolver = get_resolver()
        
        print("\nAvailable URL patterns:")
        for pattern in resolver.reverse_dict.keys():
            if isinstance(pattern, str):
                print(f"  - {pattern}")
        
        print("\nChecking for organizer URLs:")
        for pattern in resolver.reverse_dict.keys():
            if isinstance(pattern, str) and 'organizer' in pattern:
                print(f"  - {pattern}")
    
    # Get the organizer
    try:
        organizer = OrganizerRequest.objects.filter(status='approved').first()
        
        if not organizer:
            print("No approved organizer found!")
            return
        
        print(f"Found organizer: {organizer.email}, status: {organizer.status}")
        
        # Update the login_view function to directly render the organizer dashboard
        print("\nTo fix the organizer login redirect issue, update the login_view function in googlelogin/views.py:")
        print("Replace lines 364-376 with:")
        print("""
                # Direct password comparison
                if organizer.password == password:
                    print("Organizer login successful")
                    request.session['organizer_id'] = organizer.id
                    request.session['user_type'] = 'organizer'
                    request.session['organization_name'] = organizer.organization_name
                    request.session['user_id'] = organizer.id
                    request.session['organizer_email'] = organizer.email
                    request.session['organizer_logged_in'] = True
                    print(f"Updated session: {dict(request.session.items())}")
                    
                    messages.success(request, "Organizer login successful")
                    
                    # Import the organizer dashboard view and call it directly
                    from organizer.views import organizer_dashboard
                    return organizer_dashboard(request)
        """)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
