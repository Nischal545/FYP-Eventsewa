from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import re
from .models import UserProfile, Admin, Organizer, EventHistory, OrganizerRequest
from events.models import Event
import random
import smtplib
from email.message import EmailMessage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse
import base64
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
import traceback
from django.db import connection
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
from django.shortcuts import get_object_or_404
from decimal import Decimal
from datetime import datetime
from urllib.request import urlopen
from io import BytesIO
from django.template.loader import get_template
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
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, cursor.fetchone()))

def landing_page(request):
    try:
        # Get all upcoming events
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    e.id,
                    e.name,
                    e.date,
                    e.location,
                    e.capacity,
                    e.price,
                    e.is_active,
                    e.event_code,
                    COALESCE(o.organization_name, org_req.organization_name) as organizer_name
                FROM users.events e
                LEFT JOIN users.organizers o ON e.organizer_id = o.id
                LEFT JOIN users.organizer_requests org_req ON e.organizer_id = org_req.id
                WHERE e.date >= CURRENT_TIMESTAMP AND e.is_active = true
                ORDER BY e.date ASC;
            """)
            events = dictfetchall(cursor)
            
            print(f"Found {len(events)} events")
            
            # Process each event
            for event in events:
                # Format date and time (handle timezone)
                event_date = event['date'].astimezone()  # Convert to local timezone
                event['formatted_date'] = event_date.strftime('%B %d, %Y')
                event['formatted_time'] = event_date.strftime('%I:%M %p')
                
                # Set capacity info
                event['total_capacity'] = event['capacity']
                event['remaining_tickets'] = event['capacity']  # For now, showing full capacity
                event['tickets_percentage'] = 0  # No tickets sold yet
                
                # Format price
                event['formatted_price'] = f"Rs. {float(event['price']):,.2f}"
                
                print(f"Processed event: {event['name']}, Date: {event['formatted_date']}, Time: {event['formatted_time']}, Location: {event['location']}")

        return render(request, 'landing.html', {
            'events': events,
            'has_events': len(events) > 0
        })
    except Exception as e:
        print(f"Error in landing page: {str(e)}")
        traceback.print_exc()
        return render(request, 'landing.html', {
            'error': str(e),
            'events': [],
            'has_events': False
        })

def signup(request):
    return render(request, "signup.html")

def verification(request):
    if request.method == 'POST' and 'OTP_Code' in request.POST:
        user_entered_otp = request.POST.get('OTP_Code')
        generated_otp = request.session.get('generated_otp')
        email = request.session.get('signup_email')

        if not generated_otp or not email:
            messages.error(request, "Session expired or invalid. Please sign up again.")
            return redirect('googlelogin:signup')

        if user_entered_otp == generated_otp:
            print("OTP Verified")
            try:
                user_profile = UserProfile.objects.get(email=email)
                if UserProfile.objects.filter(username=user_profile.username, verification_status=True).exists():
                    messages.error(request, "Username already taken by a verified account. Please choose another.")
                    return redirect('googlelogin:signup')
                user_profile.verification_status = True
                user_profile.save()
                print(f"User {email} verified, status set to True")
                messages.success(request, "OTP verified successfully")
                del request.session['generated_otp']
                del request.session['signup_email']
                request.session['user_id'] = user_profile.id
                return redirect('users:home')
            except UserProfile.DoesNotExist:
                messages.error(request, "User not found. Please sign up again.")
                return redirect('googlelogin:signup')
        else:
            print("Invalid OTP")
            messages.error(request, "Invalid OTP")
            return render(request, 'verification.html')

    elif request.method == 'GET':
        email = request.session.get('signup_email')
        if not email:
            messages.error(request, "No email found. Please sign up again.")
            return redirect('googlelogin:signup')

        otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
        print(f"Generated OTP: {otp}")

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            from_mail = 'nischalacharya545@gmail.com'
            server.login(from_mail, 'zcae rrac lxbd dptp')
            to_mail = email

            msg = EmailMessage()
            msg['Subject'] = "OTP Verification"
            msg['From'] = from_mail
            msg['To'] = to_mail
            msg.set_content("Your OTP is: " + otp)

            server.send_message(msg)
            server.quit()

            request.session['generated_otp'] = otp
            request.session.set_expiry(300)
        except smtplib.SMTPException as e:
            print(f"SMTP error: {str(e)}")
            messages.error(request, f"Failed to send OTP: {str(e)}")
            return render(request, 'verification.html')
        except Exception as e:
            print(f"General error: {str(e)}")
            messages.error(request, "Failed to send OTP due to a network issue. Please try again.")
            return render(request, 'verification.html')

        return render(request, 'verification.html')

    return render(request, 'verification.html')

def store_input(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        gender = request.POST.get('gender')

        if not all([name, email, username, phone_number, password, gender]):
            messages.error(request, "All fields are required")
            return render(request, 'signup.html', {'form_data': request.POST})

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address")
            return render(request, 'signup.html', {'form_data': request.POST})

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long")
            return render(request, 'signup.html', {'form_data': request.POST})
        if not any(char.isupper() for char in password):
            messages.error(request, "Password must contain at least one uppercase letter")
            return render(request, 'signup.html', {'form_data': request.POST})
        if not any(char.islower() for char in password):
            messages.error(request, "Password must contain at least one lowercase letter")
            return render(request, 'signup.html', {'form_data': request.POST})
        if not any(char.isdigit() for char in password):
            messages.error(request, "Password must contain at least one number")
            return render(request, 'signup.html', {'form_data': request.POST})
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            messages.error(request, "Password must contain at least one special character")
            return render(request, 'signup.html', {'form_data': request.POST})
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'signup.html', {'form_data': request.POST})

        existing_unverified = UserProfile.objects.filter(
            Q(email=email) | Q(phone_number=phone_number),
            verification_status=False
        ).first()

        if existing_unverified:
            request.session['signup_data'] = {
                'name': name,
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'password': password,
                'gender': gender,
            }
            request.session['unverified_email'] = existing_unverified.email
            return redirect('googlelogin:delete_unverified')

        if UserProfile.objects.filter(username=username, verification_status=True).exists():
            messages.error(request, "Username is already taken by a verified account")
            return render(request, 'signup.html', {'form_data': request.POST})

        try:
            user_profile = UserProfile(
                name=name,
                email=email,
                username=username,
                phone_number=phone_number,
                password=password,
                gender=gender,
                verification_status=False
            )
            user_profile.full_clean()
            user_profile.save()
            messages.success(request, "Data saved successfully")
            request.session['signup_email'] = email
            return redirect('googlelogin:verification')
        except IntegrityError:
            error_fields = []
            if UserProfile.objects.filter(email=email, verification_status=True).exists():
                error_fields.append("Email")
            if UserProfile.objects.filter(phone_number=phone_number, verification_status=True).exists():
                error_fields.append("Phone")
            if error_fields:
                messages.error(request, f"{', '.join(error_fields)} already taken by a verified account")
            else:
                messages.error(request, "A database error occurred. Please try again")
            return render(request, 'signup.html', {'form_data': request.POST})

    signup_data = request.session.get('signup_data', {})
    if signup_data:
        del request.session['signup_data']
    return render(request, 'signup.html', {'form_data': signup_data})

def delete_unverified(request):
    if request.method == 'POST':
        unverified_email = request.session.get('unverified_email')
        if 'confirm_delete' in request.POST and unverified_email:
            try:
                user = UserProfile.objects.get(email=unverified_email, verification_status=False)
                user.delete()
                print(f"Deleted unverified account: {unverified_email}")
                messages.success(request, "Unverified account deleted. Please proceed with signup.")
                del request.session['unverified_email']
                return redirect('googlelogin:signup')
            except UserProfile.DoesNotExist:
                messages.error(request, "Unverified account not found.")
                return redirect('googlelogin:signup')
        else:
            messages.error(request, "Deletion not confirmed.")
            return render(request, 'delete_unverified.html')

    return render(request, 'delete_unverified.html')

def login_view(request):
    print("\n=== LOGIN VIEW ACCESSED ===")
    print(f"Request Method: {request.method}")
    try:
        print(f"Session data: {dict(request.session.items())}")
    except Exception as e:
        print(f"Error accessing session: {str(e)}")
        request.session = {}
    
    if request.method == 'POST':
        login_id = request.POST.get('login_id')
        password = request.POST.get('password')
        print(f"\nLogin attempt with:")
        print(f"Login ID: {login_id}")
        print(f"Password length: {len(password) if password else 0}")
        
        try:
            # First check users.admins table since it's simpler
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, password, name, type 
                    FROM users.admins 
                    WHERE username = %s
                """, [login_id])
                
                admin = cursor.fetchone()
                
                if admin:
                    print(f"Found admin:")
                    print(f"  ID: {admin[0]}")
                    print(f"  Username: {admin[1]}")
                    print(f"  Type: {admin[4]}")
                    
                    if admin[2] == password:  # Direct password comparison
                        print("Admin password matched, logging in...")
                        # Set session data for admin
                        request.session['admin_id'] = admin[0]
                        request.session['user_type'] = 'admin'
                        request.session['admin_name'] = admin[3]
                        request.session['admin_username'] = admin[1]
                        request.session['admin_type'] = admin[4]
                        request.session['is_admin'] = True  # Add this for backward compatibility
                        
                        messages.success(request, "Admin login successful!")
                        return redirect('googlelogin:admin_dashboard')
                    else:
                        print("Invalid password for admin")
                        messages.error(request, "Invalid password")
                        return render(request, 'login.html', {'form_data': request.POST})
                
                # If not an admin, check users.group1 (regular users)
                cursor.execute("""
                    SELECT id, username, email, password, name, verification_status 
                    FROM users.group1 
                    WHERE (username = %s OR email = %s)
                """, [login_id, login_id])
                
                user = cursor.fetchone()
                
                if user:
                    print(f"Found user in group1:")
                    print(f"  ID: {user[0]}")
                    print(f"  Username: {user[1]}")
                    print(f"  Email: {user[2]}")
                    print(f"  Verification: {user[5]}")
                    
                    if user[3] == password:  # Direct password comparison
                        if user[5]:  # Check verification status
                            print("User verified, logging in...")
                            # Set session data for regular user
                            request.session['user_id'] = user[0]
                            request.session['user_type'] = 'user'
                            request.session['username'] = user[1]
                            request.session['name'] = user[4]
                            request.session['email'] = user[2]
                            
                            messages.success(request, "Login successful!")
                            return redirect('users:home')
                        else:
                            print("User not verified")
                            messages.error(request, "Please verify your account first")
                            return render(request, 'login.html', {'form_data': request.POST})
                    else:
                        print("Invalid password for user")
                        messages.error(request, "Invalid password")
                        return render(request, 'login.html', {'form_data': request.POST})
                
                # Check organizer_requests table for approved organizers
                cursor.execute("""
                    SELECT id, organization_name, email, password, status, username 
                    FROM users.organizer_requests 
                    WHERE (username = %s OR email = %s) AND status = 'approved'
                """, [login_id, login_id])
                
                organizer = cursor.fetchone()
                
                if organizer:
                    print(f"Found approved organizer:")
                    print(f"  ID: {organizer[0]}")
                    print(f"  Organization: {organizer[1]}")
                    print(f"  Username: {organizer[5]}")
                    
                    if organizer[3] == password:  # Direct password comparison
                        print("Organizer password matched, logging in...")
                        # Set session data for organizer
                        request.session['organizer_id'] = organizer[0]
                        request.session['user_type'] = 'organizer'
                        request.session['organization_name'] = organizer[1]
                        request.session['organizer_email'] = organizer[2]
                        request.session['organizer_logged_in'] = True
                        request.session['organizer_username'] = organizer[5]
                        
                        messages.success(request, "Login successful!")
                        return redirect('organizer:dashboard')
                    else:
                        print("Invalid password for organizer")
                        messages.error(request, "Invalid password")
                        return render(request, 'login.html', {'form_data': request.POST})
                
                # If we get here, no valid user was found
                print("No matching user found")
                messages.error(request, "Invalid username/email or password")
                return render(request, 'login.html', {'form_data': request.POST})
                    
        except Exception as e:
            print(f"Error during login: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f"An error occurred: {str(e)}")
        
        return render(request, 'login.html', {'form_data': request.POST})
        
    return render(request, 'login.html')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Email is required")
            return render(request, 'forgot_password.html', {'form_data': request.POST})

        try:
            user = UserProfile.objects.get(email=email)
            if not user.verification_status:
                messages.error(request, "Account not verified. Please verify first.")
                return render(request, 'forgot_password.html', {'form_data': request.POST})

            reset_otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
            request.session['reset_otp'] = reset_otp
            request.session['reset_email'] = email
            request.session.set_expiry(300)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            from_mail = 'smth@gmail.com'
            server.login(from_mail, 'something')
            to_mail = email

            msg = EmailMessage()
            msg['Subject'] = "Password Reset OTP"
            msg['From'] = from_mail
            msg['To'] = to_mail
            msg.set_content(f"Your password reset OTP is: {reset_otp}")
            server.send_message(msg)
            server.quit()

            messages.success(request, "Reset OTP sent to your email")
            return redirect('reset_password')  # Placeholder
        except UserProfile.DoesNotExist:
            messages.error(request, "Email not found")
            return render(request, 'forgot_password.html', {'form_data': request.POST})
        except Exception as e:
            print(f"Email error: {str(e)}")
            messages.error(request, "Failed to send reset OTP")
            return render(request, 'forgot_password.html', {'form_data': request.POST})

    return render(request, 'forgot_password.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            with connection.cursor() as cursor:
                # Check admin credentials
                cursor.execute("""
                    SELECT id, name, email, type, password 
                    FROM users.admins 
                    WHERE username = %s
                """, [username])
                admin = cursor.fetchone()
                
                if admin and admin[4] == password:  # Index 4 is password
                    # Store admin info in session
                    request.session['admin_id'] = admin[0]
                    request.session['admin_name'] = admin[1]
                    request.session['admin_email'] = admin[2]
                    request.session['admin_type'] = admin[3]
                    request.session['is_admin'] = True
                    
                    messages.success(request, f'Welcome back, {admin[1]}!')
                    return redirect('googlelogin:admin_dashboard')
                else:
                    messages.error(request, 'Invalid username or password.')
        except Exception as e:
            messages.error(request, 'An error occurred. Please try again.')
            print(f"Login error: {str(e)}")
    
    return render(request, 'admin/login.html')

def admin_dashboard(request):
    # Check if user is logged in as admin
    if not request.session.get('admin_id') or request.session.get('user_type') != 'admin':
        messages.error(request, 'Please login first.')
        return redirect('googlelogin:login_view')
    
    context = {
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type'),
    }
    
    admin_type = request.session.get('admin_type')
    
    try:
        with connection.cursor() as cursor:
            if admin_type == 'U/O Checker':
                # Get user stats
                cursor.execute("SELECT COUNT(*) FROM users.group1")
                context['total_users'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM users.organizer_requests WHERE status = 'approved'")
                context['total_organizers'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users.group1 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                context['new_users_today'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users.organizer_requests 
                    WHERE status = 'pending'
                """)
                context['pending_verifications'] = cursor.fetchone()[0]

                # Fetch recent users
                cursor.execute("""
                    SELECT id, name, email, verification_status, created_at 
                    FROM users.group1 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                context['users'] = dictfetchall(cursor)

                # Fetch recent organizers
                cursor.execute("""
                    SELECT id, organization_name, email, status, created_at 
                    FROM users.organizer_requests 
                    WHERE status = 'approved'
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                context['organizers'] = dictfetchall(cursor)
                
            elif admin_type == 'event_checker':
                # Get event stats
                cursor.execute("""
                    SELECT COUNT(*) FROM users.events 
                    WHERE date >= CURRENT_DATE
                """)
                context['active_events'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM users.tickets")
                context['total_tickets_sold'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users.events 
                    WHERE date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
                """)
                context['upcoming_events'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COALESCE(SUM(price), 0) FROM users.tickets 
                    WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                """)
                context['total_revenue'] = cursor.fetchone()[0]

                # Fetch recent events
                cursor.execute("""
                    SELECT e.id, e.name, e.date, e.location, e.price, e.capacity,
                           o.organization_name as organizer_name
                    FROM users.events e
                    JOIN users.organizer_requests o ON e.organizer_id = o.id
                    ORDER BY e.date DESC
                    LIMIT 10
                """)
                context['events'] = dictfetchall(cursor)
                
            elif admin_type == 'request checker':
                # Get request stats
                cursor.execute("""
                    SELECT COUNT(*) FROM users.organizer_requests 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                context['new_requests'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users.organizer_requests 
                    WHERE DATE(updated_at) = CURRENT_DATE AND status = 'approved'
                """)
                context['approved_today'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM users.organizer_requests 
                    WHERE status = 'pending'
                """)
                context['total_pending'] = cursor.fetchone()[0]
                
                # Calculate average response time in hours
                cursor.execute("""
                    SELECT COALESCE(
                        AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600),
                        0
                    )::integer
                    FROM users.organizer_requests 
                    WHERE status != 'pending'
                """)
                context['avg_response_time'] = cursor.fetchone()[0]

                # Fetch pending requests
                cursor.execute("""
                    SELECT id, organization_name, email, status, created_at 
                    FROM users.organizer_requests 
                    WHERE status = 'pending'
                    ORDER BY created_at DESC
                """)
                context['pending_requests'] = dictfetchall(cursor)
            
            # Get recent activities (if table exists)
            try:
                cursor.execute("""
                    SELECT created_at, action_type, details, status 
                    FROM users.admin_activities 
                    WHERE admin_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """, [request.session.get('admin_id')])
                activities = []
                for activity in cursor.fetchall():
                    status_color = {
                        'success': 'success',
                        'pending': 'warning',
                        'error': 'danger',
                        'info': 'info'
                    }.get(activity[3], 'secondary')
                    
                    activities.append({
                        'timestamp': activity[0],
                        'action': activity[1],
                        'details': activity[2],
                        'status': activity[3],
                        'status_color': status_color
                    })
                context['recent_activities'] = activities
            except:
                # Table might not exist yet
                context['recent_activities'] = []
            
    except Exception as e:
        messages.error(request, 'Error loading dashboard data.')
        print(f"Dashboard error: {str(e)}")
    
    return render(request, 'admin/dashboard.html', context)

def approve_organizer(request, request_id):
    if request.method == 'POST':
        if 'admin_id' not in request.session or request.session.get('user_type') != 'admin':
            messages.error(request, "Please login as admin first")
            return redirect('googlelogin:login_view')
        
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            if admin.type != 'request_checker':
                messages.error(request, "Access denied. You are not a request checker.")
                return redirect('admin_dashboard')

            organizer_request = OrganizerRequest.objects.get(id=request_id)
            
            # Update request status to approved
            organizer_request.status = 'approved'
            organizer_request.save()
            
            # Create entry in Organizer table
            try:
                Organizer.objects.create(
                    user_id=organizer_request.user_id,
                    organization_name=organizer_request.organization_name,
                    username=organizer_request.username,
                    owner_names=organizer_request.owner_names,
                    email=organizer_request.email,
                    password=organizer_request.password,
                    address=organizer_request.address,
                    verification_status=True
                )
            except IntegrityError:
                messages.error(request, "Organizer already exists")
                return redirect('admin_pending_requests')
            
            # Send approval email
            try:
                subject = "EventSewa - Organizer Application Approved"
                message = f"""
                Dear {organizer_request.organization_name},

                Congratulations! Your application to become an organizer on EventSewa has been approved.
                You can now log in to your organizer dashboard using your email and password.

                Best regards,
                EventSewa Admin Team
                """
                
                send_mail(
                    subject,
                    message,
                    settings.ADMIN_EMAIL,
                    [organizer_request.email],
                    fail_silently=False,
                )
                
                messages.success(request, f"Successfully approved {organizer_request.organization_name} and sent notification email")
            except Exception as e:
                messages.warning(request, f"Organizer approved but failed to send email: {str(e)}")
            
            return redirect('admin_pending_requests')
            
        except OrganizerRequest.DoesNotExist:
            messages.error(request, "Request not found")
            
    return redirect('admin_pending_requests')

def reject_organizer(request, request_id):
    if request.method == 'POST':
        if 'admin_id' not in request.session or request.session.get('user_type') != 'admin':
            messages.error(request, "Please login as admin first")
            return redirect('googlelogin:login_view')
        
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            if admin.type != 'request_checker':
                messages.error(request, "Access denied. You are not a request checker.")
                return redirect('admin_dashboard')

            organizer_request = OrganizerRequest.objects.get(id=request_id)
            
            # Update request status
            organizer_request.status = 'rejected'
            organizer_request.save()
            
            # Send rejection email
            try:
                subject = "EventSewa - Organizer Application Status"
                message = f"""
                Dear {organizer_request.organization_name},

                We regret to inform you that your application to become an organizer on EventSewa has been rejected.
                You may submit a new application after addressing any issues with your previous application.

                Best regards,
                EventSewa Admin Team
                """
                
                send_mail(
                    subject,
                    message,
                    settings.ADMIN_EMAIL,
                    [organizer_request.email],
                    fail_silently=False,
                )
                
                messages.success(request, f"Successfully rejected and notified {organizer_request.organization_name}")
            except Exception as e:
                messages.error(request, f"Failed to send rejection email: {str(e)}")
            
            return redirect('admin_pending_requests')
            
        except OrganizerRequest.DoesNotExist:
            messages.error(request, "Request not found")
            
    return redirect('admin_pending_requests')

def admin_logout(request):
    # Clear all session data
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect('googlelogin:login_view')


def admin_profile(request):
    # Check if user is logged in as admin
    if not request.session.get('admin_id') or request.session.get('user_type') != 'admin':
        messages.error(request, 'Please login first.')
        return redirect('googlelogin:login_view')
    
    admin_id = request.session.get('admin_id')
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, name, type 
                FROM users.admins 
                WHERE id = %s
            """, [admin_id])
            
            admin = dictfetchone(cursor)
            
            if not admin:
                messages.error(request, 'Admin not found.')
                return redirect('googlelogin:login_view')
            
            # Get admin activity logs if available
            cursor.execute("""
                SELECT action, timestamp, details
                FROM users.admin_logs
                WHERE admin_id = %s
                ORDER BY timestamp DESC
                LIMIT 10
            """, [admin_id])
            
            activity_logs = dictfetchall(cursor)
    
    except Exception as e:
        print(f"Error in admin profile: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        activity_logs = []
    
    context = {
        'admin': admin,
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type'),
        'activity_logs': activity_logs
    }
    
    return render(request, 'admin/profile.html', context)

def organizer_signup(request):
    print("\n=== ORGANIZER SIGNUP START ===")
    print(f"Request Method: {request.method}")
    
    if 'user_id' not in request.session:
        print("No user_id in session")
        messages.info(request, "Please log in to become an organizer")
        return redirect('googlelogin:login_view')

    print(f"User ID from session: {request.session['user_id']}")

    try:
        user = UserProfile.objects.get(id=request.session['user_id'])
        print(f"Found user: {user.username}")
    except UserProfile.DoesNotExist:
        print("UserProfile not found")
        messages.error(request, "User not found")
        return redirect('googlelogin:login_view')

    if request.method == 'POST':
        print("\n=== Processing POST data ===")
        try:
            # Get and validate form data
            form_data = {
                'organization_name': request.POST.get('organization_name'),
                'username': request.POST.get('username'),
                'owner_names': request.POST.get('owner_names'),
                'email': request.POST.get('email'),
                'password': request.POST.get('password'),
                'confirm_password': request.POST.get('confirm_password'),
                'address': request.POST.get('address'),
                'phone': request.POST.get('phone'),
                'license_image': request.FILES.get('license_image')
            }

            print("Received form data:")
            for key, value in form_data.items():
                if key not in ['password', 'confirm_password', 'license_image']:
                    print(f"{key}: {value}")
                else:
                    print(f"{key}: {'[SET]' if value else '[NOT SET]'}")

            # Check for missing fields
            missing_fields = [field for field, value in form_data.items() if not value]
            if missing_fields:
                messages.error(request, f"Missing required fields: {', '.join(missing_fields)}")
                return render(request, 'organizer_signup.html', {'form_data': form_data})

            # Validate username uniqueness
            if OrganizerRequest.objects.filter(username=form_data['username']).exists():
                messages.error(request, "Username is already taken. Please choose another.")
                return render(request, 'organizer_signup.html', {'form_data': form_data})

            # Validate email format
            try:
                validate_email(form_data['email'])
            except ValidationError:
                messages.error(request, "Please enter a valid email address")
                return render(request, 'organizer_signup.html', {'form_data': form_data})

            # Validate password
            if len(form_data['password']) < 8:
                messages.error(request, "Password must be at least 8 characters long")
                return render(request, 'organizer_signup.html', {'form_data': form_data})
            if not any(char.isupper() for char in form_data['password']):
                messages.error(request, "Password must contain at least one uppercase letter")
                return render(request, 'organizer_signup.html', {'form_data': form_data})
            if not any(char.islower() for char in form_data['password']):
                messages.error(request, "Password must contain at least one lowercase letter")
                return render(request, 'organizer_signup.html', {'form_data': form_data})
            if not any(char.isdigit() for char in form_data['password']):
                messages.error(request, "Password must contain at least one number")
                return render(request, 'organizer_signup.html', {'form_data': form_data})
            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", form_data['password']):
                messages.error(request, "Password must contain at least one special character")
                return render(request, 'organizer_signup.html', {'form_data': form_data})
            if form_data['password'] != form_data['confirm_password']:
                messages.error(request, "Passwords do not match")
                return render(request, 'organizer_signup.html', {'form_data': form_data})

            # Check for existing email
            if OrganizerRequest.objects.filter(email=form_data['email']).exists():
                messages.error(request, "Email is already registered")
                return render(request, 'organizer_signup.html', {'form_data': form_data})

            # Hash the password
            hashed_password = make_password(form_data['password'])
            print(f"Password hashed successfully. Hash length: {len(hashed_password)}")

            # Read license image file
            license_image_data = form_data['license_image'].read()

            # Insert into organizer_requests table
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users.organizer_requests (
                        user_id, organization_name, username, owner_names, email, 
                        password, address, phone, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, [
                    user.id,
                    form_data['organization_name'],
                    form_data['username'],
                    form_data['owner_names'],
                    form_data['email'],
                    hashed_password,  # Use the hashed password
                    form_data['address'],
                    form_data['phone'],
                    'pending'
                ])
                row = cursor.fetchone()

                if row:
                    print("\nVerified in database:")
                    print(f"ID: {row[0]}")
                    print(f"Organization: {form_data['organization_name']}")
                    print(f"Username: {form_data['username']}")
                    print(f"Owners: {form_data['owner_names']}")
                    print(f"Email: {form_data['email']}")
                    print(f"Address: {form_data['address']}")
                else:
                    print("\nWARNING: Data not found in database after insert!")

            messages.success(request, 'Your organizer application has been submitted successfully! Please wait for admin verification.')
            return redirect('users:home')

        except Exception as e:
            print("\n=== ERROR OCCURRED ===")
            print(f"Error Type: {type(e)}")
            print(f"Error Message: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'organizer_signup.html')

    print("Rendering organizer signup form")
    return render(request, 'organizer_signup.html')

def organizer_dashboard(request):
    print("\n=== ORGANIZER DASHBOARD ===")
    print(f"Session data: {dict(request.session.items())}")
    
    # Check if user is logged in as organizer using either the old or new session variable
    if not request.session.get('organizer_id') or request.session.get('user_type') != 'organizer':
        messages.error(request, "Please login as an organizer first")
        return redirect('googlelogin:login_view')
    
    try:
        organizer_id = request.session.get('organizer_id')
        print(f"Looking for organizer with ID: {organizer_id}")
        
        # First try to get from OrganizerRequest table for approved organizers
        try:
            organizer = OrganizerRequest.objects.get(id=organizer_id, status='approved')
            print(f"Found organizer in OrganizerRequest: {organizer.organization_name}")
        except OrganizerRequest.DoesNotExist:
            print("Not found in OrganizerRequest, checking Organizer table")
            # If not found in OrganizerRequest, try Organizer table
            try:
                organizer = Organizer.objects.get(id=organizer_id)
                print(f"Found organizer in Organizer table: {organizer.organization_name}")
            except Organizer.DoesNotExist:
                print("Organizer not found in either table")
                messages.error(request, "Organizer account not found")
                return redirect('googlelogin:login_view')
        
        # Get events for this organizer with a corrected query
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.*, 
                       COALESCE(o.organization_name, org_req.organization_name) as organization_name,
                       e.capacity as remaining_tickets
                FROM users.events e
                LEFT JOIN users.organizers o ON e.organizer_id = o.id
                LEFT JOIN users.organizer_requests org_req ON e.organizer_id = org_req.id
                WHERE e.organizer_id = %s
                ORDER BY e.date DESC
            """, [organizer_id])
            events = dictfetchall(cursor)
            
            print(f"Found {len(events)} events for organizer")
            for event in events:
                print(f"Event: {event['name']}, Date: {event['date']}, Active: {event['is_active']}")
        
        # Calculate totals
        total_events = len(events)
        active_events = sum(1 for e in events if e.get('is_active', False))
        total_capacity = sum(e.get('capacity', 0) for e in events)
        total_revenue = sum(e.get('price', 0) * e.get('capacity', 0) for e in events)
        
        context = {
            'organizer': organizer,
            'total_events': total_events,
            'active_events': active_events,
            'total_capacity': total_capacity,
            'total_revenue': total_revenue,
            'recent_events': events[:5] if events else [],
            'organization_name': organizer.organization_name,
            'email': organizer.email,
            'phone': organizer.phone if hasattr(organizer, 'phone') else 'Not provided',
            'address': organizer.address if hasattr(organizer, 'address') else 'Not provided',
            'status': organizer.status if hasattr(organizer, 'status') else 'Approved'
        }
        
        print("Rendering organizer dashboard with context:", context)
        return render(request, 'organizer/dashboard.html', context)
        
    except Exception as e:
        print(f"Error in organizer dashboard: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('googlelogin:login_view')

def test_email(request):
    try:
        subject = "Test Email from EventSewa"
        message = "This is a test email to verify the email configuration is working correctly."
        from_email = settings.EMAIL_HOST_USER
        recipient_list = ['nischalnov@gmail.com']  # Your email address
        
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        return HttpResponse("Test email sent successfully!")
    except Exception as e:
        return HttpResponse(f"Failed to send email: {str(e)}")

def admin_users_list(request):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    context = {
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type')
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, verification_status, created_at 
                FROM users.group1 
                ORDER BY created_at DESC
            """)
            context['users'] = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, 'Error loading users.')
        print(f"Error: {str(e)}")
    
    return render(request, 'admin/users_list.html', context)

def admin_organizers_list(request):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    context = {
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type')
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, organization_name, email, status, created_at 
                FROM users.organizer_requests 
                ORDER BY created_at DESC
            """)
            context['organizers'] = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, 'Error loading organizers.')
        print(f"Error: {str(e)}")
    
    return render(request, 'admin/organizers_list.html', context)

def admin_events_list(request):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    context = {
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type')
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.name, e.date, e.location, e.price, e.capacity,
                       o.organization_name as organizer_name
                FROM users.events e
                JOIN users.organizer_requests o ON e.organizer_id = o.id
                ORDER BY e.date DESC
            """)
            context['events'] = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, 'Error loading events.')
        print(f"Error: {str(e)}")
    
    return render(request, 'admin/events_list.html', context)

def admin_event_history(request):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    context = {
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type')
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.name, e.date, e.location, 
                       COUNT(t.id) as tickets_sold,
                       o.organization_name as organizer_name
                FROM users.events e
                JOIN users.organizer_requests o ON e.organizer_id = o.id
                LEFT JOIN users.tickets t ON e.id = t.event_id
                WHERE e.date < CURRENT_DATE
                GROUP BY e.id, e.name, e.date, e.location, o.organization_name
                ORDER BY e.date DESC
            """)
            context['past_events'] = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, 'Error loading event history.')
        print(f"Error: {str(e)}")
    
    return render(request, 'admin/event_history.html', context)

def admin_pending_requests(request):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    context = {
        'admin_name': request.session.get('admin_name'),
        'admin_type': request.session.get('admin_type')
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, organization_name, email, status, created_at 
                FROM users.organizer_requests 
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)
            context['pending_requests'] = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, 'Error loading pending requests.')
        print(f"Error: {str(e)}")
    
    return render(request, 'admin/pending_requests.html', context)

def manage_user(request, user_id):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            with connection.cursor() as cursor:
                if action == 'verify':
                    cursor.execute("""
                        UPDATE users.group1 
                        SET verification_status = 'verified' 
                        WHERE id = %s
                    """, [user_id])
                elif action == 'block':
                    cursor.execute("""
                        UPDATE users.group1 
                        SET verification_status = 'blocked' 
                        WHERE id = %s
                    """, [user_id])
                messages.success(request, f'User successfully {action}ed.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('googlelogin:admin_users_list')

def manage_organizer(request, organizer_id):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            with connection.cursor() as cursor:
                if action == 'approve':
                    cursor.execute("""
                        UPDATE users.organizer_requests 
                        SET status = 'approved' 
                        WHERE id = %s
                    """, [organizer_id])
                elif action == 'reject':
                    cursor.execute("""
                        UPDATE users.organizer_requests 
                        SET status = 'rejected' 
                        WHERE id = %s
                    """, [organizer_id])
                messages.success(request, f'Organizer successfully {action}d.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('googlelogin:admin_organizers_list')

def manage_event(request, event_id):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            with connection.cursor() as cursor:
                if action == 'approve':
                    cursor.execute("""
                        UPDATE users.events 
                        SET is_active = true 
                        WHERE id = %s
                    """, [event_id])
                elif action == 'block':
                    cursor.execute("""
                        UPDATE users.events 
                        SET is_active = false 
                        WHERE id = %s
                    """, [event_id])
                messages.success(request, f'Event successfully {action}d.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('googlelogin:admin_events_list')

def manage_request(request, request_id):
    if not request.session.get('is_admin'):
        return redirect('googlelogin:admin_login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            with connection.cursor() as cursor:
                if action == 'approve':
                    cursor.execute("""
                        UPDATE users.organizer_requests 
                        SET status = 'approved', 
                            updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, [request_id])
                elif action == 'reject':
                    cursor.execute("""
                        UPDATE users.organizer_requests 
                        SET status = 'rejected', 
                            updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, [request_id])
                messages.success(request, f'Request successfully {action}d.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('googlelogin:admin_pending_requests')

def direct_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            with connection.cursor() as cursor:
                # Check if user exists
                cursor.execute("""
                    SELECT id, password, verification_status 
                    FROM users.group1 
                    WHERE username = %s
                """, [username])
                user = dictfetchone(cursor)
                
                if user and check_password(password, user['password']):
                    if user['verification_status'] == 'verified':
                        # Set session variables
                        request.session['user_id'] = user['id']
                        request.session['username'] = username
                        request.session['is_authenticated'] = True
                        messages.success(request, 'Login successful!')
                        return redirect('users:dashboard')
                    else:
                        messages.error(request, 'Please verify your email first.')
                else:
                    messages.error(request, 'Invalid username or password.')
        except Exception as e:
            messages.error(request, 'An error occurred during login.')
            print(f"Login error: {str(e)}")
    
    return render(request, 'googlelogin/login.html')

def direct_organizer_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            with connection.cursor() as cursor:
                # Check if organizer exists and is approved
                cursor.execute("""
                    SELECT id, organization_name, email, password, status 
                    FROM users.organizer_requests 
                    WHERE (username = %s OR email = %s) AND status = 'approved'
                """, [username, username])
                organizer = dictfetchone(cursor)
                
                if organizer and check_password(password, organizer['password']):
                    # Set session variables
                    request.session['organizer_id'] = organizer['id']
                    request.session['organization_name'] = organizer['organization_name']
                    request.session['organizer_email'] = organizer['email']
                    request.session['organizer_logged_in'] = True
                    messages.success(request, 'Login successful!')
                    return redirect('googlelogin:organizer_dashboard')
                else:
                    messages.error(request, 'Invalid credentials or account not approved.')
        except Exception as e:
            messages.error(request, 'An error occurred during login.')
            print(f"Login error: {str(e)}")
    
    return render(request, 'googlelogin/login.html')

def event_details(request, event_id):
    try:
        with connection.cursor() as cursor:
            # Get event details
            cursor.execute("""
                SELECT e.id, e.name, e.date, e.location, e.capacity, e.price, 
                       e.is_active, e.event_code, o.organization_name as organizer_name
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

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)