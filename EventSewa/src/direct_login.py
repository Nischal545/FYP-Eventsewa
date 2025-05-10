import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from googlelogin.models import UserProfile
from django.db.models import Q

def create_session(request):
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    request.session.save()

def main():
    # Create a fake request
    factory = RequestFactory()
    request = factory.get('/')
    
    # Add session to request
    create_session(request)
    
    # Find the user
    username = 'nisha123'
    user = UserProfile.objects.filter(
        Q(username=username) | Q(email=username)
    ).first()
    
    if not user:
        print(f"User {username} not found!")
        return
    
    print(f"Found user: {user.username}, verification_status: {user.verification_status}")
    
    # Set session variables
    request.session['user_id'] = user.id
    request.session['user_type'] = 'user'
    request.session['username'] = user.username
    request.session['name'] = user.name
    request.session['email'] = user.email
    
    # Save the session key
    session_key = request.session.session_key
    print(f"Session key: {session_key}")
    print(f"Session data: {dict(request.session.items())}")
    
    print("\nTo use this session, run the following command in your browser console:")
    print(f"document.cookie = 'sessionid={session_key}; path=/;'")
    print("\nThen navigate to: http://127.0.0.1:8000/users/home/")

if __name__ == "__main__":
    main()
