import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.urls import reverse, resolve, NoReverseMatch
from googlelogin.models import OrganizerRequest
from django.contrib import messages
from django.shortcuts import render, redirect
import traceback

def main():
    print("=== FIXING ORGANIZER REDIRECT ISSUE ===")
    
    # 1. Verify the organizer exists with correct credentials
    try:
        organizer = OrganizerRequest.objects.filter(username='organization').first()
        
        if not organizer:
            print("ERROR: No organizer found with username 'organization'")
            return
        
        print(f"Found organizer:")
        print(f"  Username: {organizer.username}")
        print(f"  Email: {organizer.email}")
        print(f"  Password: {organizer.password}")
        print(f"  Status: {organizer.status}")
        
        if organizer.status != 'approved':
            print("WARNING: Organizer status is not 'approved'")
            organizer.status = 'approved'
            organizer.save()
            print("Fixed: Updated organizer status to 'approved'")
    
    except Exception as e:
        print(f"Error checking organizer: {str(e)}")
        traceback.print_exc()
        return
    
    # 2. Check URL configuration
    try:
        dashboard_url = reverse('organizer:dashboard')
        print(f"\nOrganizer dashboard URL: {dashboard_url}")
        print("URL configuration is correct")
    except NoReverseMatch:
        print("\nERROR: Could not find URL for 'organizer:dashboard'")
        print("This means there's an issue with the URL configuration")
        return
    
    # 3. Fix the login_view function in googlelogin/views.py
    print("\nTo fix the organizer login issue, update the login_view function in googlelogin/views.py:")
    print("""
    # Find this section in login_view function:
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
        
        # REPLACE THIS LINE:
        # return redirect('organizer:dashboard')
        
        # WITH THIS:
        return redirect('/organizer/dashboard/')
    """)
    
    # 4. Create a direct access link
    print("\nAlternatively, use this direct access URL to bypass the login process:")
    print("http://127.0.0.1:8000/direct-organizer-login/")
    
    print("\nIf you're still having issues, check the following:")
    print("1. Make sure the organizer app is included in INSTALLED_APPS in settings.py")
    print("2. Make sure the organizer URLs are included in the main urls.py file")
    print("3. Check for any login_required decorators in the organizer views")

if __name__ == "__main__":
    main()
