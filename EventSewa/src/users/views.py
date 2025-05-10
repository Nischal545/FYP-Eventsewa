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
        
        # Get user tickets for the tickets section
        tickets = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT t.id as ticket_id, t.is_used, e.name as event_name, e.date as event_date, e.location as event_location
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
                       o.organization_name as organizer_name
                FROM users.events e
                JOIN users.organizers o ON e.organizer_id = o.id
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
        
        # Get user's event history (you'll need to adjust this based on your model structure)
        # This assumes you have a model for ticket purchases that links to events
        tickets = user.tickets.all().order_by('-purchase_date')
        
        # Process event data for display
        history_data = []
        for ticket in tickets:
            event = ticket.event
            history_item = {
                'event_name': event.name,
                'event_date': event.date,
                'purchase_date': ticket.purchase_date,
                'num_tickets': ticket.quantity,
                'total_amount': ticket.total_amount,
                'status': ticket.status,
                'event_image': base64.b64encode(event.image).decode('utf-8') if event.image else None
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
        purchase_details = request.session['purchase_details']
        event_id = purchase_details['event_id']
        num_tickets = purchase_details['num_tickets']
        total_amount = purchase_details['total_amount']
        
        # Get event details using raw SQL with correct column name
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.name, e.location, e.date, e.price, e.capacity, e.event_code,
                       o.organization_name as organizer_name
                FROM users.events e
                JOIN users.organizers o ON e.organizer_id = o.id
                WHERE e.id = %s
            """, [event_id])
            event = dictfetchone(cursor)
            
            if not event:
                messages.error(request, "Event not found.")
                return redirect('users:home')

        # Generate unique transaction ID (must be unique for each transaction)
        transaction_uuid = f"EV{event_id}T{int(time.time())}"
        
        # Calculate amounts (all amounts in paisa - multiply by 100)
        amount = int(float(total_amount))  # total_amount is already in rupees
        tax_amount = 0  # Set according to your tax rules
        service_charge = 0
        delivery_charge = 0
        total_amount = amount + tax_amount + service_charge + delivery_charge

        # eSewa v2 signature generation
        # 1. Create the message string in exact order
        message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code=EPAYTEST"
        
        # 2. Generate signature using HMAC-SHA256
        secret_key = '8gBm/:&EnhH.1/q'  # eSewa test secret key
        signature = base64.b64encode(
            hmac.new(
                secret_key.encode('utf-8'), 
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')

        # eSewa payment parameters for v2
        esewa_params = {
            'amount': str(amount),  # in rupees
            'tax_amount': str(tax_amount),
            'total_amount': str(total_amount),  # in rupees
            'transaction_uuid': transaction_uuid,
            'product_code': 'EPAYTEST',
            'product_service_charge': str(service_charge),
            'product_delivery_charge': str(delivery_charge),
            'success_url': request.build_absolute_uri(reverse('users:payment_success')),
            'failure_url': request.build_absolute_uri(reverse('users:payment_failure')),
            'signed_field_names': 'total_amount,transaction_uuid,product_code',
            'signature': signature
        }
        
        # Store purchase details in session for verification
        request.session['esewa_purchase'] = {
            'event_id': event_id,
            'num_tickets': num_tickets,
            'total_amount': total_amount,
            'transaction_uuid': transaction_uuid
        }
        
        return render(request, 'users/payment.html', {
            'event': event,
            'num_tickets': num_tickets,
            'total_amount': total_amount,  # Already in rupees
            'esewa_params': esewa_params,
            'test_mode': True
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
        oid = request.GET.get('oid')
        amt = request.GET.get('amt')
        refId = request.GET.get('refId')
        
        # Get purchase details from session
        purchase_details = request.session['esewa_purchase']
        event_id = purchase_details['event_id']
        num_tickets = purchase_details['num_tickets']
        total_amount = purchase_details['total_amount']
        
        # Get event details
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.name, e.event_code, e.price, e.capacity
                FROM users.events e
                WHERE e.id = %s
            """, [event_id])
            event = dictfetchone(cursor)
            
            if not event:
                messages.error(request, "Event not found.")
                return redirect('users:home')
            
            # Generate table name (event_title_eventcode)
            table_name = f"{event['name'].lower().replace(' ', '')}_{event['event_code']}"
            
            # Get user details
            user_id = request.session['user_id']
            cursor.execute("""
                SELECT name, email
                FROM users.userprofile
                WHERE id = %s
            """, [user_id])
            user = dictfetchone(cursor)
            
            if not user:
                messages.error(request, "User not found.")
                return redirect('users:home')
            
            # Insert tickets into the event-specific table
            for i in range(num_tickets):
                ticket_code = f"{event['event_code']}-{user_id}-{i+1}"
                cursor.execute(f"""
                    INSERT INTO events.{table_name} 
                    (user_name, paid_amount, num_individuals, capacity, purchase_date, 
                     user_email, ticket_code, payment_status, description)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s)
                """, [
                    user['name'],
                    float(event['price']),
                    1,  # num_individuals
                    event['capacity'],
                    user['email'],
                    ticket_code,
                    'completed',
                    f"Ticket purchased via eSewa. Payment ID: {refId or 'DUMMY-PAYMENT'}"
                ])
            
            # Update event capacity
            cursor.execute("""
                UPDATE users.events
                SET capacity = capacity - %s
                WHERE id = %s
            """, [num_tickets, event_id])
            
            # Clear session data
            if 'purchase_details' in request.session:
                del request.session['purchase_details']
            if 'esewa_purchase' in request.session:
                del request.session['esewa_purchase']
            
            messages.success(request, f"Payment successful! You have booked {num_tickets} ticket(s) for {event['name']}.")
            return redirect('users:history')
            
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect('users:payment_failure')

def payment_failure(request):
    # Clear any payment session data
    if 'purchase_details' in request.session:
        del request.session['purchase_details']
    if 'esewa_purchase' in request.session:
        del request.session['esewa_purchase']
    
    # Display failure message
    messages.error(request, "Payment was unsuccessful. Please try again later.")
    return redirect('users:home')

def event_details(request, event_id):
    try:
        with connection.cursor() as cursor:
            # Get event details
            cursor.execute("""
                SELECT e.id, e.name, e.date, e.location, e.capacity, e.price, 
                       e.is_active, e.event_code, o.name as organizer_name
                FROM users.events e
                JOIN users.organizers o ON e.organizer_id = o.id
                WHERE e.id = %s AND e.is_active = true
            """, [event_id])
            
            event = cursor.fetchone()
            
            if not event:
                messages.error(request, "Event not found or is not active.")
                return redirect('users:home')
            
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
                'formatted_date': event[2].strftime('%B %d, %Y'),
                'formatted_time': event[2].strftime('%I:%M %p'),
                'formatted_price': f"Rs. {event[5]:,.2f}"
            }
            
            return render(request, 'users/event_details.html', {'event': event_data})
            
    except Exception as e:
        print(f"Error fetching event details: {str(e)}")
        messages.error(request, "Error fetching event details.")
        return redirect('users:home')

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
