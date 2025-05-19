from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import UserProfile
from googlelogin.models import Organizer
from events.models import Event
from django.utils import timezone
import base64
from django.db.models import Q
from datetime import datetime
from django.urls import reverse
from django.conf import settings
import requests
from django.db.models import Sum
import traceback
import time
from events.event_table import EventTable
from googlelogin.models import EventHistory
from django.db import connection
from django.db.utils import OperationalError
from django.db import connection
from django.db.utils import OperationalError
import hmac
import hashlib
import random
import string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import smtplib
from email.message import EmailMessage

def dictfetchall(cursor):
    """Return all rows from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def dictfetchone(cursor):
    """Return one row from a cursor as a dict"""
    row = cursor.fetchone()
    if row:
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))
    return None

def home(request):
    print("\n=== HOME VIEW ACCESSED ===")
    print(f"Session data: {dict(request.session.items())}")
    
    if not request.session.get('user_id'):
        messages.error(request, "Please login first")
        return redirect('googlelogin:login_view')
    
    # Get upcoming events
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.*, 
                       COALESCE(o.organization_name, org_req.organization_name) as organizer_name
                FROM users.events e
                LEFT JOIN users.organizers o ON e.organizer_id = o.id
                LEFT JOIN users.organizer_requests org_req ON e.organizer_id = org_req.id
                WHERE e.date >= CURRENT_DATE AND e.is_active = true
                ORDER BY e.date ASC
            """)
            events = dictfetchall(cursor)
            
            # Process events for display
            for event in events:
                # Add image data if available
                if event.get('image'):
                    try:
                        event['image_base64'] = base64.b64encode(event['image']).decode('utf-8')
                    except Exception as e:
                        print(f"Error processing image: {str(e)}")
                        event['image_base64'] = None
                else:
                    event['image_base64'] = None
    except Exception as e:
        print(f"Error fetching events: {str(e)}")
        events = []
    
    context = {
        'name': request.session.get('name', 'User'),
        'events': events,
        'query': ''
    }
    
    return render(request, 'users/home.html', context)

def dashboard(request):
    if not request.session.get('user_id'):
        messages.error(request, "Please login first")
        return redirect('googlelogin:login_view')
    
    # Get search parameters
    query = request.GET.get('q', '')
    date = request.GET.get('date', '')
    location = request.GET.get('location', '')
    
    try:
        user_id = request.session.get('user_id')
        
        # Get user tickets for the tickets section from event_history
        tickets = []
        try:
            with connection.cursor() as cursor:
                # First check if the event_history table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'users' AND table_name = 'event_history'
                    )
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    # Create the event_history table if it doesn't exist
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users.event_history (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            event_id INTEGER NOT NULL,
                            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            num_tickets INTEGER NOT NULL,
                            total_amount NUMERIC NOT NULL,
                            payment_method VARCHAR(50) NOT NULL,
                            payment_id VARCHAR(100) NOT NULL
                        )
                    """)
                
                # Get tickets from event_history
                cursor.execute("""
                    SELECT h.id as ticket_id, false as is_used, e.name as event_name, 
                           e.date as event_date, e.location as event_location,
                           h.purchase_date, h.num_tickets, h.total_amount, h.payment_method,
                           e.id as event_id
                    FROM users.event_history h
                    JOIN users.events e ON h.event_id = e.id
                    WHERE h.user_id = %s
                    ORDER BY h.purchase_date DESC
                    LIMIT 10
                """, [user_id])
                tickets = dictfetchall(cursor)
                
                # If no tickets found in event_history, try the old tickets table as fallback
                if not tickets:
                    cursor.execute("""
                        SELECT t.id as ticket_id, t.is_used, e.name as event_name, 
                               e.date as event_date, e.location as event_location,
                               e.id as event_id
                        FROM users.tickets t
                        JOIN users.events e ON t.event_id = e.id
                        WHERE t.user_id = %s
                        ORDER BY e.date DESC
                        LIMIT 5
                    """, [user_id])
                    tickets = dictfetchall(cursor)
        except Exception as e:
            print(f"Error fetching tickets: {str(e)}")
        
        # Get upcoming events with search filters
        try:
            with connection.cursor() as cursor:
                # Base query
                sql_query = """
                    SELECT e.*, 
                           COALESCE(o.organization_name, org_req.organization_name) as organizer_name
                    FROM users.events e
                    LEFT JOIN users.organizers o ON e.organizer_id = o.id
                    LEFT JOIN users.organizer_requests org_req ON e.organizer_id = org_req.id
                    WHERE e.date >= CURRENT_DATE AND e.is_active = true
                """
                
                # Add search filters
                params = []
                
                if query:
                    sql_query += " AND (e.name ILIKE %s OR COALESCE(o.organization_name, org_req.organization_name) ILIKE %s)"
                    params.extend([f'%{query}%', f'%{query}%'])
                
                if date:
                    try:
                        search_date = datetime.strptime(date, '%Y-%m-%d').date()
                        sql_query += " AND DATE(e.date) = %s"
                        params.append(search_date)
                    except ValueError:
                        pass
                
                if location:
                    sql_query += " AND e.location ILIKE %s"
                    params.append(f'%{location}%')
                
                # Add order by and execute
                sql_query += " ORDER BY e.date ASC"
                
                cursor.execute(sql_query, params)
                events = dictfetchall(cursor)
                
                # Process events for display
                for event in events:
                    # Add image data if available
                    if event.get('image'):
                        try:
                            event['image_base64'] = base64.b64encode(event['image']).decode('utf-8')
                        except Exception as img_error:
                            print(f"Error processing image: {str(img_error)}")
                            event['image_base64'] = None
                    else:
                        event['image_base64'] = None
        except Exception as e:
            print(f"Error fetching events: {str(e)}")
            events = []
        
        # Get stats for dashboard
        tickets_count = 0
        upcoming_events_count = 0
        past_events_count = 0
        favorites_count = 0
        
        try:
            with connection.cursor() as cursor:
                # Check if event_history table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'users' AND table_name = 'event_history'
                    )
                """)
                event_history_exists = cursor.fetchone()[0]
                
                if event_history_exists:
                    # Count tickets from event_history (sum of num_tickets for each purchase)
                    cursor.execute("""
                        SELECT COALESCE(SUM(num_tickets), 0) 
                        FROM users.event_history 
                        WHERE user_id = %s
                    """, [user_id])
                    result = cursor.fetchone()
                    tickets_count = int(result[0]) if result and result[0] else 0
                    
                    # Count upcoming events (tickets for future events)
                    cursor.execute("""
                        SELECT COALESCE(SUM(h.num_tickets), 0) 
                        FROM users.event_history h
                        JOIN users.events e ON h.event_id = e.id
                        WHERE h.user_id = %s AND e.date >= CURRENT_DATE
                    """, [user_id])
                    result = cursor.fetchone()
                    upcoming_events_count = int(result[0]) if result and result[0] else 0
                    
                    # Count past events
                    cursor.execute("""
                        SELECT COALESCE(SUM(h.num_tickets), 0) 
                        FROM users.event_history h
                        JOIN users.events e ON h.event_id = e.id
                        WHERE h.user_id = %s AND e.date < CURRENT_DATE
                    """, [user_id])
                    result = cursor.fetchone()
                    past_events_count = int(result[0]) if result and result[0] else 0
                else:
                    # Fallback to old tickets table if event_history doesn't exist
                    # Count tickets
                    cursor.execute("SELECT COUNT(*) FROM users.tickets WHERE user_id = %s", [user_id])
                    result = cursor.fetchone()
                    tickets_count = result[0] if result else 0
                    
                    # Count upcoming events (tickets for future events)
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM users.tickets t
                        JOIN users.events e ON t.event_id = e.id
                        WHERE t.user_id = %s AND e.date >= CURRENT_DATE
                    """, [user_id])
                    result = cursor.fetchone()
                    upcoming_events_count = result[0] if result else 0
                    
                    # Count past events
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM users.tickets t
                        JOIN users.events e ON t.event_id = e.id
                        WHERE t.user_id = %s AND e.date < CURRENT_DATE
                    """, [user_id])
                    result = cursor.fetchone()
                    past_events_count = result[0] if result else 0
                
                # Count favorites (if favorites table exists)
                try:
                    cursor.execute("SELECT COUNT(*) FROM users.favorites WHERE user_id = %s", [user_id])
                    result = cursor.fetchone()
                    favorites_count = result[0] if result else 0
                except:
                    # Favorites table might not exist
                    favorites_count = 0
        except Exception as e:
            print(f"Error fetching stats: {str(e)}")
        
        context = {
            'name': request.session.get('name', 'User'),
            'events': events,
            'tickets': tickets,
            'query': query,
            'date': date,
            'location': location,
            'tickets_count': tickets_count,
            'upcoming_events_count': upcoming_events_count,
            'past_events_count': past_events_count,
            'favorites_count': favorites_count
        }
        
        return render(request, 'users/dashboard.html', context)
    except Exception as e:
        print(f"Error in dashboard view: {str(e)}")
        traceback.print_exc()
        messages.error(request, "An error occurred while loading your dashboard.")
        return render(request, 'users/dashboard.html', {'name': request.session.get('name', 'User')})

def organizer_signup(request):
    if request.method == 'POST':
        organization_name = request.POST.get('organization_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        license_image = request.FILES.get('license_image')

        if not all([organization_name, email, phone, address, license_image]):
            messages.error(request, "All fields are required")
            return render(request, 'organizer_signup.html', {'form_data': request.POST})

        try:
            # Save to database or handle file upload
            print("Organization Name:", organization_name)
            print("Email:", email)
            print("Phone:", phone)
            print("Address:", address)
            print("License Image:", license_image)

            messages.success(request, "Organizer sign-up submitted successfully")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'organizer_signup.html', {'form_data': request.POST})

    return render(request, 'organizer_signup.html')

def search(request):
    query = request.GET.get('q', '')
    date = request.GET.get('date', '')

    try:
        # Start with all active events
        events = Event.objects.filter(
            is_active=True
        ).order_by('date')

        # Apply search filters
        if query:
            events = events.filter(
                Q(name__icontains=query) |
                Q(organizer__organization_name__icontains=query)
            )

        if date:
            try:
                search_date = datetime.strptime(date, '%Y-%m-%d').date()
                # Filter events for the specific date
                events = events.filter(date__date=search_date)
            except ValueError:
                messages.warning(request, "Invalid date format. Please use the date picker.")

        # Convert images to base64 for display
        events_data = []
        for event in events:
            event_data = {
                'id': event.id,
                'name': event.name,
                'location': event.location,
                'date': event.date,
                'price': float(event.price),
                'capacity': event.capacity,
                'description': event.description,
                'event_code': event.event_code if hasattr(event, 'event_code') else None,
                'organizer_name': event.organizer.organization_name if hasattr(event, 'organizer') else '',
                'image_base64': base64.b64encode(event.image).decode('utf-8') if hasattr(event, 'image') and event.image else None
            }
            events_data.append(event_data)

        context = {
            'events': events_data,
            'query': query,
            'date': date
        }
    except Exception as e:
        # If events table doesn't exist or any other error occurs
        context = {
            'events': [],
            'query': query,
            'date': date,
            'error_message': 'Events are not available at the moment.'
        }
    
    return render(request, 'home.html', context)

def profile(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to access your profile")
        return redirect('googlelogin:login_view')

    try:
        user_id = request.session['user_id']
        profile = get_object_or_404(UserProfile, id=user_id)

        if request.method == 'POST':
            form_type = request.POST.get('form_type', '')
            
            # Handle personal information update
            if form_type == 'personal_info':
                # Get current values for validation
                original_email = profile.email
                original_phone = profile.phone_number if hasattr(profile, 'phone_number') else None

                # Update fields (only allowed fields)
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                profile.name = f"{first_name} {last_name}"
                
                # Email is read-only in our form
                new_phone = request.POST.get('phone')
                profile.address = request.POST.get('address', profile.address)
                profile.bio = request.POST.get('bio', getattr(profile, 'bio', ''))

                # Validate unique fields for phone if it's changed
                if new_phone and new_phone != original_phone and UserProfile.objects.filter(phone_number=new_phone).exists():
                    messages.error(request, "Phone number already in use")
                    return redirect('users:profile')

                # Update profile
                profile.phone_number = new_phone
                
                profile.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('users:profile')
                
            # Handle profile picture upload
            elif form_type == 'profile_picture':
                if 'profile_picture' in request.FILES:
                    profile.image = request.FILES['profile_picture'].read()
                    profile.save()
                    messages.success(request, "Profile picture updated successfully!")
                    return redirect('users:profile')
                else:
                    messages.error(request, "No image file provided")
                    return redirect('users:profile')

        # Convert image to base64 for display
        image_base64 = None
        if profile.image:
            try:
                image_base64 = base64.b64encode(profile.image).decode('utf-8')
            except Exception as e:
                print(f"Error encoding profile image: {str(e)}")

        # Get upcoming events for the user dashboard
        try:
            # Get all active events
            upcoming_events = Event.objects.filter(
                is_active=True,
                date__gt=timezone.now()  # Only future events
            ).order_by('date')[:6]  # Limit to 6 events
            
            # Process events for display
            for event in upcoming_events:
                # Convert image to base64 for display
                if event.image:
                    try:
                        event.image_base64 = base64.b64encode(event.image).decode('utf-8')
                    except Exception as img_error:
                        print(f"Error processing image for event {event.id}: {str(img_error)}")
                        event.image_base64 = None
                else:
                    event.image_base64 = None
                    
                # Add organizer name
                try:
                    event.organizer_name = event.organizer.organization_name
                except:
                    event.organizer_name = "Unknown Organizer"
        except Exception as e:
            print(f"Error fetching events: {str(e)}")
            upcoming_events = []
        
        # Get user tickets for the tickets tab
        tickets = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT t.id as ticket_id, t.is_used, e.name as event_name, e.date as event_date
                    FROM users.tickets t
                    JOIN users.events e ON t.event_id = e.id
                    WHERE t.user_id = %s
                    ORDER BY e.date DESC
                    LIMIT 5
                """, [user_id])
                tickets = dictfetchall(cursor)
        except Exception as e:
            print(f"Error fetching tickets: {str(e)}")
        
        # Split name into first and last name for the form
        name_parts = profile.name.split(' ', 1) if profile.name else ['', '']
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Prepare context with all necessary data
        context = {
            'user': {
                'first_name': first_name,
                'last_name': last_name,
                'email': profile.email,
                'phone': getattr(profile, 'phone_number', ''),
                'address': getattr(profile, 'address', ''),
                'bio': getattr(profile, 'bio', ''),
                'email_notifications': getattr(profile, 'email_notifications', True),
                'event_reminders': getattr(profile, 'event_reminders', True),
                'marketing_emails': getattr(profile, 'marketing_emails', False)
            },
            'profile': profile,
            'image_base64': image_base64,
            'name': profile.name,
            'email': profile.email,
            'tickets': tickets,
            'user_events': upcoming_events
        }
        return render(request, 'users/profile.html', context)

    except Exception as e:
        print(f"Error in profile view: {str(e)}")
        traceback.print_exc()
        messages.error(request, "An error occurred while loading your profile. Please try again.")
        
        # Instead of redirecting, render the profile page with minimal context
        return render(request, 'users/profile.html', {
            'name': request.session.get('name', ''),
            'email': request.session.get('email', ''),
            'error': True
        })

def buy_ticket(request, event_id):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to purchase tickets.")
        return redirect('googlelogin:login_view')
    
    try:
        with connection.cursor() as cursor:
            # Get event details
            cursor.execute("""
                SELECT e.id, e.name, e.location, e.date, e.price, e.capacity, e.event_code,
                       COALESCE(o.organization_name, org_req.organization_name) as organizer_name
                FROM users.events e
                LEFT JOIN users.organizers o ON e.organizer_id = o.id
                LEFT JOIN users.organizer_requests org_req ON e.organizer_id = org_req.id
                WHERE e.id = %s AND e.is_active = true
            """, [event_id])
            event = dictfetchone(cursor)
            
            if not event:
                messages.error(request, "Event not found or is no longer active.")
                return redirect('users:home')
            
            # Format event data
            event_data = {
                'id': event['id'],
                'name': event['name'],
                'location': event['location'],
                'date': event['date'],
                'price': float(event['price']),
                'capacity': event['capacity'],
                'event_code': event['event_code'],
                'organizer_name': event['organizer_name']
            }
            
            if request.method == 'POST':
                num_tickets = int(request.POST.get('num_tickets', 1))
                
                # Validate number of tickets
                if num_tickets > event['capacity']:
                    messages.error(request, f"Sorry, only {event['capacity']} tickets are available.")
                    return render(request, 'users/buy_ticket.html', {'event': event_data})
                
                # Store purchase details in session for payment processing
                request.session['purchase_details'] = {
                    'event_id': event['id'],
                    'num_tickets': num_tickets,
                    'total_amount': float(event['price'] * num_tickets)
                }
                
                # Redirect to payment page
                messages.success(request, "Proceeding to payment...")
                return redirect('users:payment')
                
            return render(request, 'users/buy_ticket.html', {'event': event_data})
            
    except Exception as e:
        print(f"Error in buy_ticket view: {str(e)}")
        traceback.print_exc()
        messages.error(request, "An error occurred while processing your request.")
        return redirect('users:home')

def settings(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to access settings")
        return redirect(f'/login/?next=/users/settings/')

    try:
        user_id = request.session['user_id']
        user = get_object_or_404(UserProfile, id=user_id)
        return render(request, 'users/settings.html', {'user': user})
    except Exception as e:
        messages.error(request, f"Error accessing settings: {str(e)}")
        return redirect('users:home')

def change_password(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to change your password")
        return redirect('googlelogin:login_view')
        
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            user = get_object_or_404(UserProfile, id=user_id)

            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            # Validate inputs
            if not all([current_password, new_password, confirm_password]):
                messages.error(request, "All fields are required")
                return redirect('users:profile')

            # In a real application, you would verify the password hash
            # This is a simplified check - replace with proper password verification
            if hasattr(user, 'check_password') and callable(getattr(user, 'check_password')):
                if not user.check_password(current_password):
                    messages.error(request, "Current password is incorrect")
                    return redirect('users:profile')
            elif hasattr(user, 'password') and user.password != current_password:
                messages.error(request, "Current password is incorrect")
                return redirect('users:profile')

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match")
                return redirect('users:profile')

            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long")
                return redirect('users:profile')

            # Update password - use set_password if available, otherwise update directly
            if hasattr(user, 'set_password') and callable(getattr(user, 'set_password')):
                user.set_password(new_password)
            else:
                user.password = new_password
                
            user.save()

            messages.success(request, "Password changed successfully")
            return redirect('users:profile')
        except Exception as e:
            messages.error(request, f"Error changing password: {str(e)}")
            return redirect('users:profile')

    return redirect('users:profile')

def update_notifications(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to update notification settings")
        return redirect('googlelogin:login_view')

    if request.method != 'POST':
        return redirect('users:profile')

    try:
        user_id = request.session['user_id']
        user = get_object_or_404(UserProfile, id=user_id)

        # Update notification preferences
        user.email_notifications = request.POST.get('email_notifications') == 'on'
        user.event_reminders = request.POST.get('event_reminders') == 'on'
        user.marketing_emails = request.POST.get('marketing_emails') == 'on'
        
        # Save the changes
        user.save()

        messages.success(request, "Notification preferences updated successfully")
        return redirect('users:profile')

    except Exception as e:
        messages.error(request, f"Error updating notification settings: {str(e)}")
        return redirect('users:profile')

def update_privacy(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to update privacy settings")
        return redirect(f'/login/?next=/users/settings/')

    if request.method != 'POST':
        return redirect('users:settings')

    try:
        user_id = request.session['user_id']
        user = get_object_or_404(UserProfile, id=user_id)

        user.profile_visible = request.POST.get('profile_visible') == 'on'
        user.show_history = request.POST.get('show_history') == 'on'
        user.save()

        messages.success(request, "Privacy settings updated successfully")
        return redirect('users:settings')

    except Exception as e:
        messages.error(request, f"Error updating privacy settings: {str(e)}")
        return redirect('users:settings')

def delete_account(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to delete your account")
        return redirect('googlelogin:login_view')
        
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            user = get_object_or_404(UserProfile, id=user_id)
            
            # Delete the user account
            user.delete()
            
            # Clear session data
            request.session.flush()
            
            messages.success(request, "Your account has been successfully deleted.")
            return redirect('googlelogin:login_view')
        except Exception as e:
            messages.error(request, f"Error deleting account: {str(e)}")
            return redirect('users:profile')
    
    # For GET requests, show confirmation page
    return render(request, 'users/delete_account_confirm.html')

def history(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to view your history")
        return redirect(f'/login/?next=/users/history/')

    try:
        user_id = request.session['user_id']
        user = get_object_or_404(UserProfile, id=user_id)
        
        # Get user's event history from the event_history table using raw SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT h.id, h.event_id, h.purchase_date, h.num_tickets, h.total_amount, h.payment_method,
                       e.name as event_name, e.date as event_date, e.image as event_image
                FROM users.event_history h
                JOIN users.events e ON h.event_id = e.id
                WHERE h.user_id = %s
                ORDER BY h.purchase_date DESC
            """, [user_id])
            
            # Convert to list of dictionaries
            columns = [col[0] for col in cursor.description]
            tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Process event data for display
        history_data = []
        for ticket in tickets:
            history_item = {
                'event_name': ticket['event_name'],
                'event_date': ticket['event_date'],
                'purchase_date': ticket['purchase_date'],
                'num_tickets': ticket['num_tickets'],
                'total_amount': ticket['total_amount'],
                'status': 'Completed',  # Assuming all records in event_history are completed purchases
                # Safely handle event image which might be None or a binary object
                'event_image': base64.b64encode(ticket['event_image']).decode('utf-8') if ticket['event_image'] and isinstance(ticket['event_image'], bytes) else None
            }
            history_data.append(history_item)
        
        return render(request, 'users/history.html', {
            'history': history_data,
            'user': user
        })
        
    except Exception as e:
        messages.error(request, f"Error accessing history: {str(e)}")
        return redirect('users:home')

def delete_account(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to delete your account")
        return redirect(f'/login/?next=/users/profile/')

    try:
        user_id = request.session['user_id']
        user = get_object_or_404(UserProfile, id=user_id)
        
        # Delete the user's profile image if it exists
        if user.image:
            user.image = None
            
        # Delete the user account
        user.delete()
        
        # Clear session
        request.session.flush()
        
        messages.success(request, "Your account has been successfully deleted")
        return redirect('login_view')
        
    except Exception as e:
        messages.error(request, f"Error deleting account: {str(e)}")
        return redirect('users:profile')

def account_settings(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to access account settings.")
        return redirect('googlelogin:login_view')

    try:
        user_id = request.session['user_id']
        profile = get_object_or_404(UserProfile, id=user_id)
        
        if request.method == 'POST':
            if 'change_password' in request.POST:
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')

                # Validate current password
                if not profile.check_password(current_password):
                    messages.error(request, "Current password is incorrect.")
                    return redirect('users:account_settings')

                # Validate new password
                if new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                    return redirect('users:account_settings')

                # Update password
                profile.set_password(new_password)
                profile.save()
                messages.success(request, "Password changed successfully!")
                return redirect('users:account_settings')

        return render(request, 'users/account_settings.html', {'profile': profile})

    except Exception as e:
        messages.error(request, f"Error accessing account settings: {str(e)}")
        return redirect('users:home')

def payment(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to make a payment.")
        return redirect('googlelogin:login_view')
    
    if 'purchase_details' not in request.session:
        messages.error(request, "No purchase details found.")
        return redirect('users:home')
    
    try:
        # Get purchase details from session
        purchase_details = request.session['purchase_details']
        event_id = purchase_details['event_id']
        num_tickets = purchase_details['num_tickets']
        total_amount = purchase_details['total_amount']
        
        print(f"Processing payment for event ID: {event_id}, tickets: {num_tickets}, amount: {total_amount}")
        
        # Get event details using raw SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.name, e.location, e.date, e.price, e.capacity, e.event_code,
                       COALESCE(o.organization_name, org_req.organization_name) as organizer_name
                FROM users.events e
                LEFT JOIN users.organizers o ON e.organizer_id = o.id
                LEFT JOIN users.organizer_requests org_req ON e.organizer_id = org_req.id
                WHERE e.id = %s
            """, [event_id])
            event = dictfetchone(cursor)
            
            # We now have a comprehensive JOIN in the first query that covers both tables
            
            if not event:
                messages.error(request, "Event not found.")
                return redirect('users:home')

        # Generate unique transaction ID (must be unique for each transaction)
        transaction_uuid = f"EV{event_id}T{int(time.time())}{random.randint(1000, 9999)}"
        
        # Use the actual ticket price for the eSewa transaction - fully dynamic based on ticket price
        # This will show the real price in the eSewa payment page
        display_amount = int(float(total_amount))
        amount = display_amount  # Use the actual ticket price (dynamic)
        tax_amount = 0  # No tax
        service_charge = 0  # Explicitly set service charge to 0 as requested
        delivery_charge = 0  # No delivery charge
        total_amount_with_charges = amount  # Must match the amount for eSewa to accept it
        
        print(f"Dynamic ticket price being used: Rs. {display_amount}")  # Log to confirm dynamic pricing

        print(f"eSewa payment details: Amount: {amount}, Total: {total_amount_with_charges}, Transaction ID: {transaction_uuid}")

        # eSewa v2 signature generation
        # Create the message string in exact order as specified by eSewa
        message = f"total_amount={total_amount_with_charges},transaction_uuid={transaction_uuid},product_code=EPAYTEST"
        
        # Generate signature using HMAC-SHA256
        secret_key = '8gBm/:&EnhH.1/q'  # eSewa test secret key
        signature = base64.b64encode(
            hmac.new(
                secret_key.encode('utf-8'), 
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')

        # eSewa payment parameters for v2
        # For eSewa, amount and total_amount must be consistent
        # We'll use the actual ticket price for both fields
        esewa_params = {
            'amount': str(amount),  # The actual ticket price
            'tax_amount': str(tax_amount),
            'total_amount': str(total_amount_with_charges),  # Same as amount
            'transaction_uuid': transaction_uuid,
            'product_code': 'EPAYTEST',
            'product_service_charge': str(service_charge),
            'product_delivery_charge': str(delivery_charge),
            'success_url': request.build_absolute_uri(reverse('users:payment_success')),
            'failure_url': request.build_absolute_uri(reverse('users:payment_failure')),
            'signed_field_names': 'total_amount,transaction_uuid,product_code',
            'signature': signature
        }
        
        # Store purchase details in session for verification in success/failure handlers
        request.session['esewa_purchase'] = {
            'event_id': event_id,
            'num_tickets': num_tickets,
            'total_amount': total_amount_with_charges,  # The actual amount charged (10 rupees)
            'display_amount': display_amount,  # The original amount for display
            'transaction_uuid': transaction_uuid
        }
        
        # Save session to ensure data is persisted
        request.session.save()
        
        return render(request, 'users/payment.html', {
            'event': event,
            'num_tickets': num_tickets,
            'total_amount': display_amount,  # Display amount for UI
            'actual_amount': amount,  # Actual amount being charged (10)
            'esewa_params': esewa_params,
            'test_mode': True  # Set to False in production
        })
        
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect('users:home')

def payment_success(request):
    if 'esewa_purchase' not in request.session:
        messages.error(request, "Invalid payment session.")
        return redirect('users:home')
    
    try:
        # Get eSewa response data
        transaction_uuid = request.GET.get('transaction_uuid')
        status = request.GET.get('status')
        refId = request.GET.get('refId')
        
        print(f"eSewa payment success callback received: {dict(request.GET.items())}")
        
        # Get purchase details from session
        purchase_details = request.session['esewa_purchase']
        event_id = purchase_details['event_id']
        num_tickets = purchase_details['num_tickets']
        total_amount = purchase_details['total_amount']  # Actual amount charged (10 rupees)
        display_amount = purchase_details.get('display_amount', total_amount)  # Original amount for display/records
        session_transaction_uuid = purchase_details.get('transaction_uuid')
        
        # Verify transaction UUID if available
        if transaction_uuid and session_transaction_uuid and transaction_uuid != session_transaction_uuid:
            print(f"Transaction UUID mismatch: {transaction_uuid} vs {session_transaction_uuid}")
            messages.error(request, "Payment verification failed. Please contact support.")
            return redirect('users:payment_failure')
        
        # Get event details
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.name, e.event_code, e.price, e.capacity, e.organizer_id
                FROM users.events e
                WHERE e.id = %s
            """, [event_id])
            event = dictfetchone(cursor)
            
            if not event:
                messages.error(request, "Event not found.")
                return redirect('users:home')
            
            # Generate table name (event_name_eventcode) with proper formatting
            table_name = f"{event['name'].lower().replace(' ', '_')}_{event['event_code'].lower()}"
            print(f"Using table name: {table_name}")
            
            # Get user details
            user_id = request.session['user_id']
            cursor.execute("""
                SELECT id, name, email
                FROM group1
                WHERE id = %s
            """, [user_id])
            user = dictfetchone(cursor)
            
            if not user:
                messages.error(request, "User not found.")
                return redirect('users:home')
            
            # Get organizer name for the event
            cursor.execute("""
                SELECT o.organization_name
                FROM organizers o
                WHERE o.id = %s
            """, [event['organizer_id']])
            organizer_result = cursor.fetchone()
            organizer_name = organizer_result[0] if organizer_result else 'Unknown Organizer'
            print(f"Event organizer: {organizer_name}")
            
            # Check if the event-specific table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'events' AND table_name = %s
                )
            """, [table_name])
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print(f"Table {table_name} does not exist. Creating it...")
                # Create the event-specific table if it doesn't exist
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS events.{table_name} (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        user_name VARCHAR(255),
                        user_email VARCHAR(255),
                        paid_amount NUMERIC,
                        num_individuals INTEGER,
                        capacity INTEGER,
                        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_phone VARCHAR(20),
                        ticket_code VARCHAR(50),
                        payment_status VARCHAR(20) DEFAULT 'pending',
                        payment_id VARCHAR(100),
                        organizer_name VARCHAR(255),
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            # Begin transaction
            cursor.execute("BEGIN")
            
            try:
                # Insert a single record for all tickets purchased
                ticket_code = f"{event['event_code']}-{user_id}-{int(time.time())}"
                
                # Print debug information
                print(f"Inserting tickets into table: events.{table_name}")
                print(f"User ID: {user['id']}, Name: {user['name']}, Email: {user['email']}")
                print(f"Ticket Code: {ticket_code}, Number of tickets: {num_tickets}")
                
                # Check if ticket_code column exists in the table
                cursor.execute(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'events' AND table_name = %s AND column_name = 'ticket_code'
                """, [table_name])
                ticket_code_exists = cursor.fetchone() is not None
                
                # Add ticket_code column if it doesn't exist
                if not ticket_code_exists:
                    print(f"Adding ticket_code column to events.{table_name}")
                    cursor.execute(f"""
                        ALTER TABLE events.{table_name} 
                        ADD COLUMN IF NOT EXISTS ticket_code VARCHAR(100)
                    """)
                
                # Insert ticket with correct column names and timestamp format
                current_time = datetime.now()
                if ticket_code_exists:
                    cursor.execute(f"""
                        INSERT INTO events.{table_name} 
                        (user_id, username, user_email, amount, num_individuals, capacity, 
                         payment_date, organizer_name, ticket_code)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        user['id'],
                        user['name'],
                        user['email'],
                        display_amount,  # Use the actual ticket price
                        num_tickets,  # Use the actual number of tickets purchased
                        event['capacity'],
                        current_time,  # Use the full timestamp object
                        organizer_name,  # Include the organizer name
                        ticket_code  # Include the ticket code
                    ])
                else:
                    # Insert without ticket_code if column doesn't exist and couldn't be added
                    cursor.execute(f"""
                        INSERT INTO events.{table_name} 
                        (user_id, username, user_email, amount, num_individuals, capacity, 
                         payment_date, organizer_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        user['id'],
                        user['name'],
                        user['email'],
                        display_amount,  # Use the actual ticket price
                        num_tickets,  # Use the actual number of tickets purchased
                        event['capacity'],
                        current_time,  # Use the full timestamp object
                        organizer_name  # Include the organizer name
                    ])
                
                # Check if original_capacity column exists
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'users' AND table_name = 'events' AND column_name = 'original_capacity'
                """)
                original_capacity_exists = cursor.fetchone() is not None
                
                if not original_capacity_exists:
                    # Add original_capacity column if it doesn't exist
                    cursor.execute("""
                        ALTER TABLE users.events 
                        ADD COLUMN IF NOT EXISTS original_capacity INTEGER
                    """)
                    
                    # Set original_capacity to current capacity for all events that don't have it set
                    cursor.execute("""
                        UPDATE users.events 
                        SET original_capacity = capacity 
                        WHERE original_capacity IS NULL
                    """)
                
                # Update the tickets_bought and total_amount columns in the events table
                cursor.execute("""
                    UPDATE users.events
                    SET tickets_bought = COALESCE(tickets_bought, 0) + %s,
                        total_amount = COALESCE(total_amount, 0) + %s
                    WHERE id = %s
                """, [num_tickets, display_amount, event_id])
                
                print(f"Updated users.events table: Added {num_tickets} tickets and Rs. {display_amount} to event ID {event_id}")
                
                # First create the event_history table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users.event_history (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        event_id INTEGER NOT NULL,
                        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        num_tickets INTEGER NOT NULL,
                        total_amount NUMERIC NOT NULL,
                        payment_method VARCHAR(50) NOT NULL,
                        payment_id VARCHAR(100) NOT NULL
                    )
                """)
                
                # Add entry to user's event history
                cursor.execute("""
                    INSERT INTO users.event_history
                    (user_id, event_id, purchase_date, num_tickets, total_amount, payment_method, payment_id)
                    VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s)
                """, [
                    user['id'],
                    event['id'],
                    num_tickets,
                    display_amount,  # Use original display amount for records
                    'eSewa',
                    refId or f"ESEWA-{transaction_uuid}"
                ])
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                # Get additional event details for the email
                cursor.execute("""
                    SELECT date, location
                    FROM users.events
                    WHERE id = %s
                """, [event_id])
                event_details = dictfetchone(cursor)
                
                if event_details:
                    event.update(event_details)
                
                # Send confirmation email to the user
                try:
                    # Format the event date and time
                    event_date = ''
                    event_time = ''
                    
                    if 'date' in event and event['date']:
                        if isinstance(event['date'], datetime):
                            event_date = event['date'].strftime('%A, %B %d, %Y')
                            event_time = event['date'].strftime('%I:%M %p')
                        else:
                            event_date = str(event['date'])
                    
                    # Get event location
                    event_location = event.get('location', 'TBA')
                    
                    # Prepare email content
                    subject = f"Ticket Confirmation - {event['name']}"
                    
                    # Email context
                    email_context = {
                        'user_name': user['name'],
                        'event_name': event['name'],
                        'event_date': event_date,
                        'event_time': event_time,
                        'event_location': event_location,
                        'num_tickets': num_tickets,
                        'total_amount': display_amount,
                        'payment_method': 'eSewa',
                        'transaction_id': refId or f"ESEWA-{transaction_uuid}",
                        'purchase_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'organizer_name': organizer_name
                    }
                    
                    print(f"Email context prepared: {email_context}")
                    
                    # Create HTML email content
                    html_message = f"""
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                            .header {{ background-color: #5e72e4; color: white; padding: 20px; text-align: center; }}
                            .content {{ padding: 20px; background-color: #f8f9fa; }}
                            .ticket-info {{ margin: 20px 0; }}
                            .ticket-info p {{ margin: 5px 0; }}
                            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
                            .button {{ display: inline-block; background-color: #5e72e4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>Ticket Confirmation</h1>
                            </div>
                            <div class="content">
                                <p>Greetings {email_context['user_name']},</p>
                                <p>Thank you for purchasing tickets through EventSewa! Your booking has been confirmed.</p>
                                
                                <div class="ticket-info">
                                    <h2>Event Details:</h2>
                                    <p><strong>Event:</strong> {email_context['event_name']}</p>
                                    <p><strong>Date:</strong> {email_context['event_date']}</p>
                                    <p><strong>Time:</strong> {email_context['event_time']}</p>
                                    <p><strong>Location:</strong> {email_context['event_location']}</p>
                                    <p><strong>Organizer:</strong> {email_context['organizer_name']}</p>
                                    <p><strong>Number of Tickets:</strong> {email_context['num_tickets']}</p>
                                    <p><strong>Total Amount:</strong> Rs. {email_context['total_amount']}</p>
                                    <p><strong>Payment Method:</strong> {email_context['payment_method']}</p>
                                    <p><strong>Transaction ID:</strong> {email_context['transaction_id']}</p>
                                    <p><strong>Purchase Date:</strong> {email_context['purchase_date']}</p>
                                </div>
                                
                                <p>Please keep this email as your ticket confirmation. You can also view your tickets in your account dashboard.</p>
                                <p>We hope you enjoy the event!</p>
                                <p>Best regards,<br>The EventSewa Team</p>
                            </div>
                            <div class="footer">
                                <p>This is an automated email. Please do not reply to this message.</p>
                                <p>&copy; {datetime.now().year} EventSewa. All rights reserved.</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Create plain text version of the email
                    plain_message = f"""Greetings {email_context['user_name']},

Thank you for purchasing tickets through EventSewa! Your booking has been confirmed.

Event Details:
- Event: {email_context['event_name']}
- Date: {email_context['event_date']}
- Time: {email_context['event_time']}
- Location: {email_context['event_location']}
- Organizer: {email_context['organizer_name']}
- Number of Tickets: {email_context['num_tickets']}
- Total Amount: Rs. {email_context['total_amount']}
- Payment Method: {email_context['payment_method']}
- Transaction ID: {email_context['transaction_id']}
- Purchase Date: {email_context['purchase_date']}

Please keep this email as your ticket confirmation. You can also view your tickets in your account dashboard.

We hope you enjoy the event!

Best regards,
The EventSewa Team
"""
                    
                    # Log email details for debugging
                    print(f"Preparing to send email to {user['email']}")
                    
                    try:
                        # Use direct SMTP approach like in googlelogin/views.py
                        import smtplib
                        from email.message import EmailMessage
                        
                        # Set up SMTP server
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        from_mail = 'nischalacharya545@gmail.com'  # Same as in googlelogin
                        server.login(from_mail, 'zcae rrac lxbd dptp')  # Same password as in googlelogin
                        to_mail = user['email']
                        
                        # Create email message
                        msg = EmailMessage()
                        msg['Subject'] = subject
                        msg['From'] = from_mail
                        msg['To'] = to_mail
                        
                        # Set plain text content
                        msg.set_content(plain_message)
                        
                        # Add HTML version
                        msg.add_alternative(html_message, subtype='html')
                        
                        # Send email
                        server.send_message(msg)
                        server.quit()
                        
                        print(f"Confirmation email sent to {user['email']} using direct SMTP")
                    except Exception as email_error:
                        print(f"Error during email sending: {str(email_error)}")
                        traceback.print_exc()
                        # Continue with process even if email fails
                    
                except Exception as email_error:
                    print(f"Error sending confirmation email: {str(email_error)}")
                    # Continue with the process even if email fails
                
                # Clear session data
                if 'purchase_details' in request.session:
                    del request.session['purchase_details']
                if 'esewa_purchase' in request.session:
                    del request.session['esewa_purchase']
                
                messages.success(request, f"Payment successful! You have booked {num_tickets} ticket(s) for {event['name']}. A confirmation email has been sent to your email address.")
                return redirect('users:history')
                
            except Exception as e:
                # Rollback transaction on error
                cursor.execute("ROLLBACK")
                raise e
            
    except Exception as e:
        print(f"Error processing payment success: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect('users:payment_failure')

def payment_failure(request):
    try:
        # Log the failure details
        print(f"Payment failure callback received: {dict(request.GET.items())}")
        
        # Get any error message from eSewa
        error_message = request.GET.get('error_message', 'Unknown error')
        transaction_uuid = request.GET.get('transaction_uuid')
        
        # Get purchase details from session if available
        purchase_details = {}
        if 'esewa_purchase' in request.session:
            purchase_details = request.session['esewa_purchase']
            print(f"Payment failure for transaction: {purchase_details.get('transaction_uuid')}")
            
            # Log purchase details for debugging
            event_id = purchase_details.get('event_id')
            num_tickets = purchase_details.get('num_tickets')
            total_amount = purchase_details.get('total_amount')
            print(f"Failed payment details - Event ID: {event_id}, Tickets: {num_tickets}, Amount: {total_amount}")
            
            # Record the failed payment attempt in database if needed
            try:
                with connection.cursor() as cursor:
                    # Create the payment_failures table if it doesn't exist
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users.payment_failures (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER,
                            event_id INTEGER,
                            amount NUMERIC,
                            transaction_uuid VARCHAR(100),
                            error_message TEXT,
                            attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Record the failure
                    cursor.execute("""
                        INSERT INTO users.payment_failures 
                        (user_id, event_id, amount, transaction_uuid, error_message, attempt_time)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, [
                        request.session.get('user_id'),
                        event_id,
                        total_amount,
                        transaction_uuid or purchase_details.get('transaction_uuid'),
                        error_message
                    ])
            except Exception as e:
                print(f"Could not record payment failure: {str(e)}")
                # Continue even if recording fails
        
        # Clear payment session data
        if 'purchase_details' in request.session:
            del request.session['purchase_details']
        if 'esewa_purchase' in request.session:
            del request.session['esewa_purchase']
        
        # Display appropriate failure message
        if error_message and error_message != 'Unknown error':
            messages.error(request, f"Payment failed: {error_message}. Please try again later.")
        else:
            messages.error(request, "Payment was unsuccessful. Please try again later.")
            
        return redirect('users:home')
        
    except Exception as e:
        print(f"Error handling payment failure: {str(e)}")
        traceback.print_exc()
        messages.error(request, "Payment was unsuccessful. Please try again later.")
        return redirect('users:home')

def event_details(request, event_id):
    # Print debug information at the start of the function
    print(f"Entering event_details function with event_id: {event_id}")
    
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "Please log in to view event details.")
            return redirect('googlelogin:login_view')
            
        with connection.cursor() as cursor:
            # Get event details
            cursor.execute("""
                SELECT e.id, e.name, e.date, e.location, e.capacity, e.price, 
                       e.is_active, e.event_code, o.organization_name as organizer_name,
                       e.organizer_id
                FROM users.events e
                LEFT JOIN users.organizers o ON e.organizer_id = o.id
                WHERE e.id = %s
            """, [event_id])
            
            event = cursor.fetchone()
            
            if not event:
                # Try with a different join if the first one fails
                cursor.execute("""
                    SELECT e.id, e.name, e.date, e.location, e.capacity, e.price, 
                           e.is_active, e.event_code, o.organization_name as organizer_name,
                           e.organizer_id
                    FROM users.events e
                    LEFT JOIN users.organizer_requests o ON e.organizer_id = o.id
                    WHERE e.id = %s
                """, [event_id])
                event = cursor.fetchone()
            
            if not event:
                messages.error(request, "Event not found.")
                return redirect('users:home')
            
            # Check if tickets_bought column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'users' AND table_name = 'events' AND column_name = 'tickets_bought'
                )
            """)
            tickets_bought_exists = cursor.fetchone()[0]
            
            # Get attendees count from the tickets_bought column if it exists, otherwise count from event_history
            if tickets_bought_exists:
                cursor.execute("""
                    SELECT COALESCE(tickets_bought, 0) as attendees_count
                    FROM users.events
                    WHERE id = %s
                """, [event_id])
                attendees_count = cursor.fetchone()[0] or 0
            else:
                # Fallback: Count from event_history table
                cursor.execute("""
                    SELECT COUNT(*) as attendees_count
                    FROM users.event_history
                    WHERE event_id = %s
                """, [event_id])
                attendees_count = cursor.fetchone()[0] or 0
            
            # Print debug information
            print(f"Event ID: {event_id}, Attendees Count (from tickets_bought): {attendees_count}")
            
            # Check if original_capacity column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'users' AND table_name = 'events' AND column_name = 'original_capacity'
                )
            """)
            original_capacity_exists = cursor.fetchone()[0]
            
            # Get the original capacity if the column exists, otherwise use the current capacity
            if original_capacity_exists:
                cursor.execute("""
                    SELECT original_capacity
                    FROM users.events
                    WHERE id = %s
                """, [event_id])
                original_capacity_result = cursor.fetchone()
                original_capacity = original_capacity_result[0] if original_capacity_result and original_capacity_result[0] else event[4]
            else:
                # If original_capacity column doesn't exist, use the current capacity
                original_capacity = event[4]
            
            # Print debug information
            print(f"Original Capacity: {original_capacity}, Current Capacity: {event[4]}")
            
            # Calculate remaining tickets based on original capacity and actual successful purchases
            remaining_tickets = max(0, original_capacity - attendees_count)
            ticket_percentage = min(100, int((attendees_count / original_capacity) * 100)) if original_capacity > 0 else 0
            
            # Print debug information
            print(f"Remaining Tickets: {remaining_tickets}, Ticket Percentage: {ticket_percentage}%")
            
            # Format event data
            event_data = {
                'id': event[0],
                'name': event[1],
                'date': event[2],
                'location': event[3],
                'capacity': event[4],
                'price': event[5],
                'is_active': event[6],
                'event_code': event[7],
                'organizer_name': event[8],
                'organizer_id': event[9],
                'formatted_date': event[2].strftime('%B %d, %Y') if isinstance(event[2], datetime) else event[2],
                'formatted_time': event[2].strftime('%I:%M %p') if isinstance(event[2], datetime) else '',
                'formatted_price': f"Rs. {event[5]:,.2f}",
                'attendees_count': attendees_count,
                'remaining_tickets': remaining_tickets,
                'ticket_percentage': ticket_percentage
            }
            
            # Check if user has purchased tickets for this event
            # First check event_history
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'users' AND table_name = 'event_history'
                )
            """)
            event_history_exists = cursor.fetchone()[0]
            
            user_tickets = []
            if event_history_exists:
                cursor.execute("""
                    SELECT h.id, h.purchase_date, h.num_tickets, h.total_amount, h.payment_method, h.payment_id
                    FROM users.event_history h
                    WHERE h.user_id = %s AND h.event_id = %s
                    ORDER BY h.purchase_date DESC
                """, [user_id, event_id])
                user_tickets = dictfetchall(cursor)
            
            # If no tickets found in event_history, try the old tickets table
            if not user_tickets:
                cursor.execute("""
                    SELECT t.id, t.purchase_date, 1 as num_tickets, t.price as total_amount, 'Unknown' as payment_method
                    FROM users.tickets t
                    WHERE t.user_id = %s AND t.event_id = %s
                """, [user_id, event_id])
                user_tickets = dictfetchall(cursor)
            
            # Get the event-specific table name
            table_name = f"{event_data['name'].lower().replace(' ', '_')}_{event_data['event_code'].lower()}"
            
            # Check if the event-specific table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'events' AND table_name = %s
                )
            """, [table_name])
            table_exists = cursor.fetchone()[0]
            
            # Get tickets from event-specific table if it exists
            event_tickets = []
            if table_exists:
                cursor.execute(f"""
                    SELECT * FROM events.{table_name}
                    LIMIT 5
                """)
                event_tickets = dictfetchall(cursor)
            
            return render(request, 'users/event_details.html', {
                'event': event_data,
                'user_tickets': user_tickets,
                'event_tickets': event_tickets,
                'has_tickets': len(user_tickets) > 0
            })
            
    except Exception as e:
        print(f"Error fetching event details: {str(e)}")
        traceback.print_exc()
        
        # Instead of redirecting to home, render a custom error page
        # or render the event_details template with error information
        messages.error(request, f"Error fetching event details: {str(e)}")
        
        # Create a basic event data structure to avoid template errors
        event_data = {
            'id': event_id,
            'name': 'Event Information Unavailable',
            'date': datetime.now(),
            'location': 'Unknown',
            'capacity': 0,
            'price': 0,
            'is_active': False,
            'event_code': 'N/A',
            'organizer_name': 'Unknown',
            'organizer_id': 0,
            'formatted_date': datetime.now().strftime('%B %d, %Y'),
            'formatted_time': datetime.now().strftime('%I:%M %p'),
            'formatted_price': 'Rs. 0.00',
            'attendees_count': 0,
            'remaining_tickets': 0,
            'ticket_percentage': 0
        }
        
        return render(request, 'users/event_details.html', {
            'event': event_data,
            'user_tickets': [],
            'event_tickets': [],
            'has_tickets': False,
            'error_occurred': True
        })

def host_event(request):
    if 'user_id' not in request.session:
        messages.error(request, "Please log in to host an event.")
        return redirect('googlelogin:login_view')
    
    try:
        if request.method == 'POST':
            # Get form data with proper validation
            name = request.POST.get('title', '').strip()
            location = request.POST.get('venue', '').strip()
            date = request.POST.get('event_date', '').strip()
            start_time = request.POST.get('start_time', '').strip()
            end_time = request.POST.get('end_time', '').strip()
            
            try:
                price = float(request.POST.get('ticket_price', '0').strip() or '0')
            except (ValueError, TypeError) as e:
                print(f"Error converting price: {str(e)}")
                messages.error(request, "Invalid price value")
                return render(request, 'organizer/host_event.html')
                
            try:
                capacity = int(request.POST.get('capacity', '0').strip() or '0')
            except (ValueError, TypeError) as e:
                print(f"Error converting capacity: {str(e)}")
                messages.error(request, "Invalid capacity value")
                return render(request, 'organizer/host_event.html')
            
            # Validate required fields
            if not all([name, location, date, start_time]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'organizer/host_event.html')
            
            # Validate numeric values
            if capacity <= 0:
                messages.error(request, "Capacity must be greater than 0.")
                return render(request, 'organizer/host_event.html')
                
            if price < 0:
                messages.error(request, "Price cannot be negative.")
                return render(request, 'organizer/host_event.html')
            
            # Validate and convert date and time
            try:
                datetime_str = f"{date} {start_time}"
                event_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                if event_datetime <= datetime.now():
                    messages.error(request, "Event date and time must be in the future.")
                    return render(request, 'organizer/host_event.html')
            except ValueError as e:
                print(f"Date/time conversion error: {str(e)}")
                messages.error(request, "Please enter valid date and time.")
                return render(request, 'organizer/host_event.html')
            
            # Generate a unique 6-character event code
            event_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Get organizer ID from session
            organizer_id = request.session.get('user_id')
            if not organizer_id:
                messages.error(request, "Invalid organizer session.")
                return redirect('googlelogin:login_view')
            
            # Start database transaction
            with connection.cursor() as cursor:
                try:
                    # Begin transaction
                    cursor.execute("BEGIN")
                    
                    # First verify the organizer exists
                    cursor.execute("""
                        SELECT id FROM users.organizers WHERE id = %s
                    """, [organizer_id])
                    
                    if not cursor.fetchone():
                        raise Exception("Invalid organizer ID")
                    
                    # Get current timestamp for created_at and updated_at
                    current_time = datetime.now(timezone.utc)
                    
                    # Insert event into database
                    cursor.execute("""
                        INSERT INTO users.events 
                        (name, location, date, price, capacity, event_code, 
                         organizer_id, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s, %s)
                        RETURNING id
                    """, [name, location, event_datetime, price, capacity, 
                         event_code, organizer_id, current_time, current_time])
                    
                    event_id = cursor.fetchone()[0]
                    
                    # Create event-specific table
                    table_name = f"event_{event_code.lower()}"
                    
                    cursor.execute(f"""
                        CREATE TABLE IF NOT EXISTS events.{table_name} (
                            id SERIAL PRIMARY KEY,
                            user_name VARCHAR(255) NOT NULL,
                            paid_amount DECIMAL(10,2) NOT NULL,
                            num_individuals INTEGER NOT NULL,
                            capacity INTEGER NOT NULL,
                            purchase_date TIMESTAMP NOT NULL,
                            user_email VARCHAR(255) NOT NULL,
                            ticket_code VARCHAR(255) NOT NULL,
                            payment_status VARCHAR(50) NOT NULL,
                            description TEXT
                        )
                    """)
                    
                    # Commit transaction
                    cursor.execute("COMMIT")
                    messages.success(request, f"Event '{name}' hosted successfully!")
                    return redirect('users:home')
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    print(f"Database error: {str(e)}")
                    messages.error(request, f"Error hosting event: {str(e)}")
                    return render(request, 'organizer/host_event.html')
        
        return render(request, 'organizer/host_event.html')
        
    except Exception as e:
        print(f"Unexpected error in host_event view: {str(e)}")
        messages.error(request, "An unexpected error occurred while hosting the event.")
        return render(request, 'organizer/host_event.html')
