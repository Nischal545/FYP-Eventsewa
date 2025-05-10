import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.test import Client
from django.urls import reverse

def main():
    print("=== TESTING ORGANIZER LOGIN ===")
    
    # Create a test client
    client = Client()
    
    # Test login with organizer credentials
    login_data = {
        'login_id': 'organization',
        'password': 'Nischal123..'
    }
    
    print(f"Attempting login with username: {login_data['login_id']}, password: {login_data['password']}")
    
    # Get the login URL
    login_url = reverse('googlelogin:login_view')
    print(f"Login URL: {login_url}")
    
    # Attempt login
    response = client.post(login_url, login_data, follow=True)
    
    # Check the response
    print(f"Response status code: {response.status_code}")
    print(f"Final URL after redirects: {response.redirect_chain[-1][0] if response.redirect_chain else 'No redirects'}")
    
    # Check if we're on the dashboard
    if 'dashboard' in response.redirect_chain[-1][0] if response.redirect_chain else '':
        print("SUCCESS: Redirected to dashboard!")
    else:
        print("FAILURE: Not redirected to dashboard")
    
    # Check session data
    print("\nSession data:")
    for key, value in client.session.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
