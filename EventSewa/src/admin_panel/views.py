from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Admin
from googlelogin.models import Event, UserProfile, Organizer, EventHistory, OrganizerRequest
from django.utils import timezone
import sys
from django.db.models import Q
import traceback
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
import base64

print("ADMIN PANEL VIEWS.PY LOADED")  # This will print when the file is loaded

def admin_login(request):
    print("\n=== ADMIN LOGIN DEBUG ===")
    print(f"Request Method: {request.method}")
    print(f"Session data: {dict(request.session.items())}")
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        print(f"\nLogin attempt:")
        print(f"Username: {username}")
        print(f"Password: {'*' * len(password)}")
        
        try:
            # Try to get the admin user
            admin = Admin.objects.get(username=username)
            print(f"\nFound admin user:")
            print(f"ID: {admin.id}")
            print(f"Username: {admin.username}")
            print(f"Type: {admin.type}")
            
            # Check password using Django's password hashing
            if check_password(password, admin.password):
                print("\nPassword matched!")
                # Set session data
                request.session['admin_id'] = admin.id
                request.session['admin_username'] = admin.username
                request.session['admin_name'] = admin.name
                request.session['admin_type'] = admin.type
                request.session['admin_logged_in'] = True
                
                print("\nSession data set:")
                print(dict(request.session.items()))
                
                messages.success(request, f'Welcome back, {admin.name}!')
                return redirect('admin_panel:admin_dashboard')
            else:
                print("\nPassword did not match!")
                messages.error(request, 'Invalid password')
        except Admin.DoesNotExist:
            print(f"\nNo admin found with username: {username}")
            messages.error(request, 'Invalid username')
        except Exception as e:
            print(f"\nError during login: {str(e)}")
            messages.error(request, f'An error occurred: {str(e)}')
    
    print("\nRendering login template")
    return render(request, 'admin_panel/login.html')

def admin_dashboard(request):
    if not request.session.get('admin_logged_in'):
        messages.error(request, 'Please login first')
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session.get('admin_id'))
        admin_type = admin.type.lower().replace(' ', '_')
        context = {'admin': admin}

        if admin_type == 'request_checker':
            # Get request counts and show most recent first
            requests = OrganizerRequest.objects.all()
            context.update({
                'pending_count': requests.filter(status='pending').count(),
                'approved_count': requests.filter(status='approved').count(),
                'rejected_count': requests.filter(status='rejected').count(),
                'recent_requests': requests.order_by('-created_at')[:5],
                'request_growth': calculate_growth_percentage(requests)
            })
            return render(request, 'admin_request_dashboard.html', context)
            
        elif admin_type == 'u/o_checker' or admin_type == 'uo_checker':
            try:
                # Get all users and their verification status
                users = UserProfile.objects.all()
                verified_users = users.filter(verification_status=True)
                
                # Calculate pending users (not verified)
                pending_users = users.count() - verified_users.count()
                
                # Get approved organizer requests
                approved_requests = OrganizerRequest.objects.filter(status='approved')
                
                # Get verified users who are also approved organizers
                verified_organizer_emails = approved_requests.values_list('email', flat=True)
                verified_organizers = verified_users.filter(email__in=verified_organizer_emails)
                
                # Calculate pending organizers (those with status='pending')
                pending_organizers = OrganizerRequest.objects.filter(status='pending').count()
                
                context.update({
                    'total_users': users.count(),
                    'verified_users': verified_users.count(),
                    'pending_users': pending_users,
                    'total_organizers': approved_requests.count(),
                    'verified_organizers': verified_organizers.count(),
                    'pending_organizers': pending_organizers,
                    'recent_users': users.order_by('-signup_date')[:5],
                    'recent_organizers': [
                        {
                            'user': request.user,
                            'organization_name': req.organization_name,
                            'email': req.email,
                            'is_verified': verified_users.filter(email=req.email).exists(),
                            'created_at': req.created_at
                        }
                        for req in approved_requests.order_by('-created_at')[:5]
                    ],
                    'user_growth': calculate_growth_percentage(users),
                    'organizer_growth': calculate_growth_percentage(approved_requests)
                })
            except Exception as e:
                print(f"Error getting organizer stats: {str(e)}")
                context.update({
                    'total_users': UserProfile.objects.count(),
                    'verified_users': UserProfile.objects.filter(verification_status=True).count(),
                    'pending_users': 0,
                    'total_organizers': 0,
                    'verified_organizers': 0,
                    'pending_organizers': 0,
                    'recent_users': UserProfile.objects.all().order_by('-signup_date')[:5],
                    'recent_organizers': [],
                    'user_growth': calculate_growth_percentage(UserProfile.objects.all()),
                    'organizer_growth': 0
                })
            return render(request, 'admin_uo_dashboard.html', context)
            
        elif admin_type == 'event_checker':
            try:
                # Get event counts
                now = timezone.now()
                events = Event.objects.all()
                
                # Get pending verification count
                pending_verification = EventHistory.objects.filter(
                    occurrence_status='pending'
                ).count()
                
                context.update({
                    'total_events': events.count(),
                    'active_events': events.filter(is_active=True, date__gte=now).count(),
                    'past_events': events.filter(date__lt=now).count(),
                    'pending_verification': pending_verification,
                    'recent_events': events.order_by('-created_at')[:5],
                    'event_history': EventHistory.objects.all().order_by('-created_at')[:5],
                    'event_growth': calculate_growth_percentage(events),
                    'now': now  # Pass current time to template for date comparisons
                })
            except Exception as e:
                print(f"Error getting event stats: {str(e)}")
                context.update({
                    'total_events': 0,
                    'active_events': 0,
                    'past_events': 0,
                    'pending_verification': 0,
                    'recent_events': [],
                    'event_history': [],
                    'event_growth': 0,
                    'now': timezone.now()
                })
            return render(request, 'admin/event_dashboard.html', context)  # Changed template path
            
        else:
            print(f"\nInvalid admin type: {admin.type}")
            messages.error(request, f'Invalid admin type: {admin.type}. Expected: request_checker, u/o_checker, or event_checker')
            return redirect('admin_panel:admin_login')
            
    except Admin.DoesNotExist:
        messages.error(request, 'Admin account not found')
        return redirect('admin_panel:admin_login')
    except Exception as e:
        print(f"\nError in admin_dashboard: {str(e)}")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('admin_panel:admin_login')

def calculate_growth_percentage(model):
    """Calculate the growth percentage for a model compared to last month"""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    last_month = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)
    
    # Handle different date field names
    date_field = 'signup_date' if hasattr(model.model, 'signup_date') else 'created_at'
    
    # Build the filter kwargs dynamically
    current_filter = {f"{date_field}__gte": last_month}
    previous_filter = {
        f"{date_field}__gte": two_months_ago,
        f"{date_field}__lt": last_month
    }
    
    current_count = model.filter(**current_filter).count()
    previous_count = model.filter(**previous_filter).count()
    
    if previous_count == 0:
        return 100 if current_count > 0 else 0
    
    growth = ((current_count - previous_count) / previous_count) * 100
    return round(growth, 1)

def admin_logout(request):
    request.session.flush()
    return redirect('admin_panel:admin_login')

def admin_event_check(request):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        if admin.type != 'event_checker':  # This is the correct type from database
            messages.error(request, "Access denied. You are not an event checker.")
            return redirect('admin_panel:admin_dashboard')
        
        search_query = request.GET.get('search', '')
        
        # Get all events from the events schema
        events = Event.objects.all()
        
        if search_query:
            events = events.filter(
                Q(name__icontains=search_query) |
                Q(organizer__organization_name__icontains=search_query) |
                Q(location__icontains=search_query)
            )
        
        # Process events for display
        current_date = timezone.now()
        upcoming_events = []
        expired_events = []
        
        for event in events:
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
            except Exception as org_error:
                print(f"Error getting organizer name for event {event.id}: {str(org_error)}")
                event.organizer_name = "Unknown Organizer"
            
            # Get ticket count
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM events.event_{event.id}_tickets")
                    event.ticket_count = cursor.fetchone()[0]
            except Exception as e:
                print(f"Error getting ticket count for event {event.id}: {str(e)}")
                event.ticket_count = 0
            
            # Categorize as upcoming or expired
            if event.date > current_date:
                upcoming_events.append(event)
            else:
                expired_events.append(event)
        
        context = {
            'upcoming_events': upcoming_events,
            'expired_events': expired_events,
            'admin_type': admin.type,
            'search_query': search_query,
            'total_events': len(events),
            'total_upcoming': len(upcoming_events),
            'total_expired': len(expired_events)
        }
        return render(request, 'admin_event_check.html', context)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def admin_event_history(request):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        if admin.type != 'event_checker':
            messages.error(request, "Access denied. You are not an event checker.")
            return redirect('admin_panel:admin_dashboard')
        
        history = EventHistory.objects.all().order_by('-verification_date')
        context = {
            'history': history,
            'admin_type': admin.type
        }
        return render(request, 'admin_event_history.html', context)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def update_event_status(request, event_id):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        if admin.type != 'event_checker':
            messages.error(request, "Access denied. You are not an event checker.")
            return redirect('admin_panel:admin_dashboard')
        
        event = get_object_or_404(Event, id=event_id)
        status = request.POST.get('status')
        
        if status in ['success', 'failed']:
            event.status = status
            event.save()
            
            # Create event history record
            EventHistory.objects.create(
                event=event,
                admin=admin,
                occurrence_status=status,
                verification_date=timezone.now()
            )
            
            messages.success(request, f"Event status updated to {status}")
        else:
            messages.error(request, "Invalid status")
            
        return redirect('admin_panel:event_check')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def admin_users_list(request):
    print("\n" + "="*50)
    print("ADMIN USERS LIST VIEW")
    print("Session data:", request.session.items())
    
    if not request.session.get('admin_logged_in'):
        print("Admin not logged in, redirecting to login")
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session.get('admin_id'))
        if admin.type != 'U/O Checker':
            print(f"Access denied. Admin type is {admin.type}")
            messages.error(request, "Access denied. You are not a U/O checker.")
            return redirect('admin_panel:admin_dashboard')
        
        search_query = request.GET.get('search', '')
        users = UserProfile.objects.all()
        
        if search_query:
            users = users.filter(
                Q(name__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        users = users.order_by('-signup_date')
        context = {
            'users': users,
            'admin_type': admin.type,
            'admin_name': admin.name,
            'search_query': search_query
        }
        print("Rendering admin_user_management.html")
        return render(request, 'admin_user_management.html', context)
    except Admin.DoesNotExist:
        print("Admin account not found")
        messages.error(request, 'Admin account not found')
        return redirect('admin_panel:admin_login')
    except Exception as e:
        print(f"Error in admin_users_list: {str(e)}")
        messages.error(request, f'Error loading users list: {str(e)}')
        return redirect('admin_panel:admin_dashboard')

def verify_user(request, user_id):
    print("\n" + "="*50)
    print("VERIFY USER VIEW")
    print(f"User ID: {user_id}")
    print("Session data:", request.session.items())
    
    if not request.session.get('admin_logged_in'):
        print("Admin not logged in, redirecting to login")
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session.get('admin_id'))
        if admin.type != 'U/O Checker':
            print(f"Access denied. Admin type is {admin.type}")
            messages.error(request, "Access denied. You are not a U/O checker.")
            return redirect('admin_panel:admin_dashboard')
        
        user = get_object_or_404(UserProfile, id=user_id)
        if not user.verification_status:
            user.verification_status = True
            user.save()
            print(f"User {user.username} verified successfully")
            messages.success(request, f"User {user.username} has been verified successfully.")
        else:
            print(f"User {user.username} is already verified")
            messages.info(request, f"User {user.username} is already verified.")
        
        return redirect('admin_panel:users_list')
    except Admin.DoesNotExist:
        print("Admin account not found")
        messages.error(request, 'Admin account not found')
        return redirect('admin_panel:admin_login')
    except UserProfile.DoesNotExist:
        print(f"User with ID {user_id} not found")
        messages.error(request, 'User not found')
        return redirect('admin_panel:users_list')
    except Exception as e:
        print(f"Error in verify_user: {str(e)}")
        messages.error(request, f'Error verifying user: {str(e)}')
        return redirect('admin_panel:users_list')

def admin_organizers_list(request):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        if admin.type != 'U/O Checker':  # Match exact type from database
            messages.error(request, "Access denied. You are not a U/O checker.")
            return redirect('admin_panel:admin_dashboard')
        
        search_query = request.GET.get('search', '')
        print("\n=== ORGANIZER LIST DEBUG ===")
        
        # Get all verified organizers first
        organizers = Organizer.objects.all()
        print(f"Found {organizers.count()} organizers:")
        for org in organizers:
            print(f"- {org.email} (verified={org.verification_status})")
        
        if search_query:
            organizers = organizers.filter(
                Q(organization_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(owner_names__icontains=search_query)
            )
        
        # Convert to list of dicts
        organizers_list = []
        verified_emails = set()  # Keep track of emails that are already verified
        
        # Add verified organizers first
        for org in organizers:
            # Only add verified organizers
            if org.verification_status:
                organizers_list.append({
                    'id': org.id,
                    'organization_name': org.organization_name,
                    'owner_names': org.owner_names,
                    'email': org.email,
                    'address': org.address,
                    'created_at': org.created_at,
                    'status': 'verified',
                    'type': 'organizer'
                })
                verified_emails.add(org.email)
                print(f"Added verified organizer: {org.email}")
        
        # Get organizer requests that don't have a corresponding verified organizer
        organizer_requests = OrganizerRequest.objects.exclude(email__in=verified_emails)
        print(f"\nFound {organizer_requests.count()} non-duplicate requests:")
        for req in organizer_requests:
            print(f"- {req.email} (status={req.status})")
        
        if search_query:
            organizer_requests = organizer_requests.filter(
                Q(organization_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(owner_names__icontains=search_query)
            )
        
        # Add non-duplicate requests
        for req in organizer_requests:
            # Only add if not already verified
            if req.email not in verified_emails:
                organizers_list.append({
                    'id': req.id,
                    'organization_name': req.organization_name,
                    'owner_names': req.owner_names,
                    'email': req.email,
                    'address': req.address,
                    'created_at': req.created_at,
                    'status': req.status,
                    'type': 'request'
                })
                print(f"Added request: {req.email}")
        
        # Sort by created_at
        organizers_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        print("\nFinal list:")
        for org in organizers_list:
            print(f"- {org['email']} ({org['type']}, {org['status']})")
        
        context = {
            'organizers': organizers_list,
            'admin_type': admin.type,
            'search_query': search_query
        }
        return render(request, 'admin/organizers_list.html', context)
    except Exception as e:
        print(f"Error in admin_organizers_list: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def delete_user(request, user_id):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        if admin.type != 'u_o_checker':
            messages.error(request, "Access denied. You are not a U/O checker.")
            return redirect('admin_panel:admin_dashboard')
        
        user = get_object_or_404(UserProfile, id=user_id)
        user.delete()
        messages.success(request, "User deleted successfully")
        return redirect('admin_panel:users_list')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def delete_organizer(request, organizer_id):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        if admin.type != 'u_o_checker':
            messages.error(request, "Access denied. You are not a U/O checker.")
            return redirect('admin_panel:admin_dashboard')
        
        organizer = get_object_or_404(Organizer, id=organizer_id)
        organizer.delete()
        messages.success(request, "Organizer deleted successfully")
        return redirect('admin_panel:organizers_list')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def admin_pending_requests(request):
    if not request.session.get('admin_logged_in'):
        messages.error(request, 'Please login first')
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session.get('admin_id'))
        if admin.type != 'Request Checker':
            messages.error(request, 'Access denied. You are not a request checker.')
            return redirect('admin_panel:admin_dashboard')
        
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')
        
        # Get organizer requests
        requests = OrganizerRequest.objects.all()
        
        # Filter by status if not 'all'
        if status_filter != 'all':
            requests = requests.filter(status=status_filter)
        
        # Filter by search query if provided
        if search_query:
            requests = requests.filter(
                Q(organization_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(owner_names__icontains=search_query)
            )
        
        # Get latest first
        requests = requests.order_by('-created_at')
        
        # Debug info
        print("\n=== ORGANIZER REQUESTS ===")
        print(f"Total requests: {requests.count()}")
        for req in requests:
            print(f"- {req.email} (status={req.status})")
            
            # Check if organizer exists
            org = Organizer.objects.filter(email=req.email).first()
            if org:
                print(f"  * Has organizer entry: verified={org.verification_status}")
        
        context = {
            'requests': requests,
            'pending_count': OrganizerRequest.objects.filter(status='pending').count(),
            'approved_count': OrganizerRequest.objects.filter(status='approved').count(),
            'rejected_count': OrganizerRequest.objects.filter(status='rejected').count(),
            'status_filter': status_filter,
            'search_query': search_query
        }
        
        return render(request, 'admin_organizer_requests.html', context)
        
    except Exception as e:
        print(f"Error in admin_pending_requests: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def approve_organizer(request, request_id):
    if request.method == 'POST':
        if not request.session.get('admin_logged_in'):
            messages.error(request, 'Please login first')
            return redirect('admin_panel:admin_login')
        
        try:
            admin = Admin.objects.get(id=request.session.get('admin_id'))
            if admin.type.lower() != 'request checker':
                messages.error(request, 'Access denied. You are not a request checker.')
                return redirect('admin_panel:admin_dashboard')

            organizer_request = OrganizerRequest.objects.get(id=request_id)
            
            # Just update the status to approved
            organizer_request.status = 'approved'
            organizer_request.save()
                
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
            
            return redirect('admin_panel:pending_requests')
            
        except OrganizerRequest.DoesNotExist:
            messages.error(request, "Request not found")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            
    return redirect('admin_panel:pending_requests')

def reject_organizer(request, request_id):
    if request.method == 'POST':
        if 'admin_id' not in request.session:
            messages.error(request, "Please login as admin first")
            return redirect('admin_panel:admin_login')
        
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            if admin.type.lower() != 'request checker':
                messages.error(request, "Access denied. You are not a request checker.")
                return redirect('admin_panel:admin_dashboard')

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
            
            return redirect('admin_panel:pending_requests')
            
        except OrganizerRequest.DoesNotExist:
            messages.error(request, "Request not found")
            
    return redirect('admin_panel:pending_requests')

def admin_profile(request):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    try:
        admin = Admin.objects.get(id=request.session['admin_id'])
        context = {
            'admin': admin,
            'admin_type': admin.type,
            'admin_name': admin.name,
            'admin_username': admin.username,
            'admin_email': admin.email,
            'admin_since': admin.created_at
        }
        return render(request, 'admin_panel/profile.html', context)
    except Admin.DoesNotExist:
        messages.error(request, "Admin account not found")
        return redirect('admin_panel:admin_login')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('admin_panel:admin_dashboard')

def update_profile(request):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    if request.method == 'POST':
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            admin.name = request.POST.get('name')
            admin.email = request.POST.get('email')
            admin.save()
            
            request.session['admin_name'] = admin.name
            messages.success(request, "Profile updated successfully")
        except Admin.DoesNotExist:
            messages.error(request, "Admin account not found")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return redirect('admin_panel:admin_profile')

def change_password(request):
    if 'admin_id' not in request.session:
        return redirect('admin_panel:admin_login')
    
    if request.method == 'POST':
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if admin.password != current_password:
                messages.error(request, "Current password is incorrect")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match")
            else:
                admin.password = new_password
                admin.save()
                messages.success(request, "Password changed successfully")
        except Admin.DoesNotExist:
            messages.error(request, "Admin account not found")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    return redirect('admin_panel:admin_profile') 


def get_event_details(request, event_id):
    """API endpoint to get event details in JSON format"""
    if 'admin_id' not in request.session:
        return JsonResponse({'error': 'Not authorized'}, status=401)
    
    try:
        # Get the event from the database
        event = Event.objects.get(id=event_id)
        
        # Get ticket count
        ticket_count = 0
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM events.event_{event.id}_tickets")
                ticket_count = cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting ticket count: {str(e)}")
        
        # Get organizer name
        organizer_name = "Unknown Organizer"
        try:
            organizer_name = event.organizer.organization_name
        except Exception as e:
            print(f"Error getting organizer name: {str(e)}")
        
        # Convert image to base64 if available
        image_base64 = None
        if event.image:
            try:
                import base64
                image_base64 = base64.b64encode(event.image).decode('utf-8')
            except Exception as e:
                print(f"Error encoding image: {str(e)}")
        
        # Prepare event data
        event_data = {
            'id': event.id,
            'name': event.name,
            'description': event.description,
            'date': event.date.strftime('%Y-%m-%d'),
            'time': event.date.strftime('%H:%M:%S'),
            'location': event.location,
            'capacity': event.capacity,
            'price': event.price,
            'is_active': event.is_active,
            'organizer_name': organizer_name,
            'ticket_count': ticket_count,
            'image_base64': image_base64
        }
        
        return JsonResponse(event_data)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
    except Exception as e:
        print(f"Error in get_event_details: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def dashboard(request):
    if not request.session.get('is_admin'):
        messages.error(request, "Please login as admin first")
        return redirect('googlelogin:admin_login')
    return render(request, 'admin/dashboard.html')