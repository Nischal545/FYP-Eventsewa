from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from googlelogin.models import UserProfile, OrganizerRequest, Organizer
from events.models import Event
from events.event_table import EventTable
from .models import OrganizerNotification
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.db import connection
from .forms import EventForm
import random
import string
from datetime import datetime
from django.db import connection
from psycopg2.extensions import AsIs

# Helper function to replace AsIs functionality
def adapt_identifier(identifier):
    return identifier

# Helper function to convert database rows to dictionaries
def dictfetchone(cursor):
    """Return a dictionary from a database row"""
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, cursor.fetchone())) if cursor.rowcount > 0 else None

def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dictionaries"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def organizer_login(request):
    # Check if already logged in
    if request.session.get('organizer_logged_in'):
        return redirect('organizer:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Check if organizer exists and is approved
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, organization_name, email, password, verification_status 
                    FROM organizers 
                    WHERE email = %s
                """, [email])
                organizer = dictfetchone(cursor)
                
            # First try direct comparison for plain text passwords
            if organizer and (password == organizer['password'] or check_password(password, organizer['password'])):
                if organizer['verification_status'] != 'approved' and organizer['verification_status'] != True:
                    messages.error(request, 'Your account is pending approval')
                    return redirect('organizer:login')
                
                # Set session variables
                request.session['organizer_logged_in'] = True
                request.session['organizer_id'] = organizer['id']
                request.session['organization_name'] = organizer['organization_name']
                request.session['organizer_email'] = organizer['email']
                request.session.save()  # Explicitly save the session
                
                messages.success(request, 'Login successful!')
                
                # Check if there's a next parameter
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('organizer:dashboard')
            else:
                messages.error(request, 'Invalid credentials')
                return redirect('organizer:login')
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            messages.error(request, f'Error during login: {str(e)}')
            return redirect('organizer:login')
    
    return render(request, 'organizer/login.html')

def organizer_logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully")
    return redirect('googlelogin:login_view')

def dashboard(request):
    # Check if user is logged in as organizer
    if not request.session.get('organizer_id'):
        messages.error(request, "Please login as an organizer first")
        return redirect('googlelogin:login_view')
    # Get organizer ID from session
    organizer_id = request.session.get('organizer_id')
    organizer_email = request.session.get('organizer_email')
    
    print(f"Dashboard - Organizer ID from session: {organizer_id}")
    print(f"Dashboard - Session data: {dict(request.session)}")
    
    try:
        with connection.cursor() as cursor:
            # First get organizer by ID
            cursor.execute("""
                SELECT id, organization_name, email, status 
                FROM users.organizer_requests 
                WHERE id = %s
            """, [organizer_id])
            organizer = cursor.fetchone()
            
            # If not found, try by email
            if not organizer and organizer_email:
                cursor.execute("""
                    SELECT id, organization_name, email, status 
                    FROM users.organizer_requests 
                    WHERE email = %s AND status = 'approved'
                """, [organizer_email])
                organizer = cursor.fetchone()
            
            if not organizer:
                messages.error(request, 'Organizer profile not found or not approved yet.')
                return redirect('login')
                
            organizer_id = organizer[0]
            
            # First check if this organizer exists in the organizers table
            print(f"Checking if organizer exists in organizers table with ID: {organizer_id}")
            cursor.execute("""
                SELECT id FROM organizers WHERE id = %s
            """, [organizer_id])
            org_result = cursor.fetchone()
            
            # If not found by ID, try by email
            if not org_result and organizer_email:
                print(f"Checking if organizer exists in organizers table with email: {organizer_email}")
                cursor.execute("""
                    SELECT id FROM organizers WHERE email = %s
                """, [organizer_email])
                org_result = cursor.fetchone()
                
                # If found by email, update the organizer_id
                if org_result:
                    organizer_id_from_organizers = org_result[0]
                    print(f"Found organizer in organizers table with ID: {organizer_id_from_organizers}")
                else:
                    organizer_id_from_organizers = None
            else:
                organizer_id_from_organizers = organizer_id if org_result else None
            
            # Get all events for this organizer using both IDs
            print(f"Executing query to get events for organizer ID from organizer_requests: {organizer_id}")
            print(f"And organizer ID from organizers table: {organizer_id_from_organizers}")
            
            if organizer_id_from_organizers:
                # Try to find events with either organizer ID
                cursor.execute("""
                    SELECT id, name, date, location, capacity, price, is_active, event_code
                    FROM users.events 
                    WHERE organizer_id = %s OR organizer_id = %s
                    ORDER BY date DESC
                """, [organizer_id, organizer_id_from_organizers])
            else:
                # Just use the original organizer ID
                cursor.execute("""
                    SELECT id, name, date, location, capacity, price, is_active, event_code
                    FROM users.events 
                    WHERE organizer_id = %s
                    ORDER BY date DESC
                """, [organizer_id])
            
            events = []
            rows = cursor.fetchall()
            print(f"Events found for organizer ID {organizer_id}: {len(rows)}")
            
            # If no events found, try checking the events table directly to see what's there
            if len(rows) == 0:
                cursor.execute("""
                    SELECT id, name, organizer_id
                    FROM users.events
                    LIMIT 10
                """)
                all_events = cursor.fetchall()
                print(f"Sample of events in the database: {all_events}")
                
                # Also check if there are any events with this organizer's email
                if organizer_email:
                    cursor.execute("""
                        SELECT o.id, e.id, e.name
                        FROM users.events e
                        JOIN organizers o ON e.organizer_id = o.id
                        WHERE o.email = %s
                        LIMIT 10
                    """, [organizer_email])
                    email_events = cursor.fetchall()
                    print(f"Events found by organizer email {organizer_email}: {email_events}")
            
            for row in rows:
                event_id = row[0]
                event_name = row[1]
                event_code = row[7]
                
                # Create table name in the same format as host_event view
                table_name = f"{event_name.lower().replace(' ', '_')}_{event_code.lower()}"
                
                # Get ticket count for this specific event
                try:
                    # First check if the table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'events' AND table_name = %s
                        )
                    """, [table_name])
                    
                    table_exists = cursor.fetchone()[0]
                    
                    if table_exists:
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM events.%s 
                            WHERE paid_status = true
                        """, [AsIs(table_name)])
                        tickets_sold = cursor.fetchone()[0]
                    else:
                        tickets_sold = 0
                except Exception as e:
                    print(f"Error getting ticket count: {str(e)}")
                    tickets_sold = 0
                
                events.append({
                    'id': event_id,
                    'name': event_name,
                    'date': row[2],
                    'location': row[3],
                    'capacity': row[4],
                    'price': row[5],
                    'is_active': row[6],
                    'event_code': event_code,
                    'tickets_sold': tickets_sold,
                    'remaining_tickets': row[4] - tickets_sold if tickets_sold is not None else row[4]
                })
            
            # Calculate statistics
            total_events = len(events)
            active_events = sum(1 for event in events if event['is_active'])
            total_tickets_sold = sum(event['tickets_sold'] for event in events)
            total_revenue = sum(event['price'] * event['tickets_sold'] for event in events)
            
            context = {
                'organizer': {
                    'id': organizer[0],
                    'organization_name': organizer[1],
                    'email': organizer[2],
                    'status': organizer[3]
                },
                'events': events,
                'total_events': total_events,
                'active_events': active_events,
                'total_tickets_sold': total_tickets_sold,
                'total_revenue': total_revenue
            }
            
            return render(request, 'organizer/dashboard.html', context)
            
    except Exception as e:
        print(f"Dashboard error: {str(e)}")  # Add debug print
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('login')

@login_required(login_url='googlelogin:login_view')
def event_list(request):
    if not request.session.get('organizer_id'):
        return redirect('googlelogin:login_view')

    try:
        organizer_id = request.session.get('organizer_id')
        
        # First try to find events using the OrganizerRequest
        events = Event.objects.filter(organizer_request_id=organizer_id)
        
        if not events:
            # Fallback to the Organizer table
            events = Event.objects.filter(organizer_id=organizer_id)
        
        context = {
            'events': events
        }
        return render(request, 'organizer/event_list.html', context)

    except Exception as e:
        messages.error(request, f'Error loading events: {str(e)}')
        return redirect('login')

def event_detail(request, event_id):
    if not request.session.get('organizer_id'):
        messages.error(request, 'Please log in as an organizer first')
        return redirect('googlelogin:login_view')

    try:
        event = get_object_or_404(Event, id=event_id)
        
        # Check if the event belongs to this organizer
        organizer_id = request.session.get('organizer_id')
        if event.organizer_id != organizer_id and event.organizer_request_id != organizer_id:
            messages.error(request, 'You do not have permission to view this event')
            return redirect('organizer:event_list')
        
        # Calculate financial information
        gross_revenue = float(event.price) * event.capacity
        event_fee = gross_revenue * 0.1  # 10% fee
        net_revenue = gross_revenue - event_fee
        
        # Convert image to base64 for display - with proper error handling
        image_base64 = None
        if event.image:
            try:
                import base64
                # Check if image data is valid before encoding
                if isinstance(event.image, bytes) and len(event.image) > 0:
                    image_base64 = base64.b64encode(event.image).decode('utf-8')
                else:
                    print(f"Invalid image data for event {event_id}: {type(event.image)}")
            except Exception as img_error:
                print(f"Error processing image for event {event_id}: {str(img_error)}")
                # Don't let image errors prevent viewing the event
                pass
        
        # Add image and financial data to event object for template
        event.image_base64 = image_base64
        
        context = {
            'event': event,
            'gross_revenue': gross_revenue,
            'event_fee': event_fee,
            'net_revenue': net_revenue
        }
        return render(request, 'organizer/event_detail.html', context)

    except Exception as e:
        print(f"Error in event_detail: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error loading event: {str(e)}')
        return redirect('organizer:dashboard')


def deactivate_event(request, event_id):
    """Deactivate an event"""
    if not request.session.get('organizer_id'):
        messages.error(request, 'Please log in as an organizer first')
        return redirect('googlelogin:login_view')
    
    if request.method == 'POST':
        try:
            event = get_object_or_404(Event, id=event_id)
            
            # Check if the event belongs to this organizer
            organizer_id = request.session.get('organizer_id')
            if event.organizer_id != organizer_id and event.organizer_request_id != organizer_id:
                messages.error(request, 'You do not have permission to modify this event')
                return redirect('organizer:event_list')
            
            # Deactivate the event
            event.is_active = False
            event.save()
            
            messages.success(request, f'Event "{event.name}" has been deactivated')
            return redirect('organizer:event_detail', event_id=event.id)
            
        except Exception as e:
            print(f"Error deactivating event: {str(e)}")
            messages.error(request, f'Error deactivating event: {str(e)}')
            return redirect('organizer:event_detail', event_id=event_id)
    
    # If not POST, redirect to event detail
    return redirect('organizer:event_detail', event_id=event_id)


def activate_event(request, event_id):
    """Activate an event"""
    if not request.session.get('organizer_id'):
        messages.error(request, 'Please log in as an organizer first')
        return redirect('googlelogin:login_view')
    
    if request.method == 'POST':
        try:
            event = get_object_or_404(Event, id=event_id)
            
            # Check if the event belongs to this organizer
            organizer_id = request.session.get('organizer_id')
            if event.organizer_id != organizer_id and event.organizer_request_id != organizer_id:
                messages.error(request, 'You do not have permission to modify this event')
                return redirect('organizer:event_list')
            
            # Activate the event
            event.is_active = True
            event.save()
            
            messages.success(request, f'Event "{event.name}" has been activated')
            return redirect('organizer:event_detail', event_id=event.id)
            
        except Exception as e:
            print(f"Error activating event: {str(e)}")
            messages.error(request, f'Error activating event: {str(e)}')
            return redirect('organizer:event_detail', event_id=event_id)
    
    # If not POST, redirect to event detail
    return redirect('organizer:event_detail', event_id=event_id)

def create_event(request):
    if not request.session.get('organizer_logged_in'):
        return redirect('organizer:login')
    
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            try:
                # Get organizer ID from session
                organizer_id = request.session.get('organizer_id')
                if not organizer_id:
                    messages.error(request, 'Organizer ID not found in session')
                    return redirect('organizer:login')
                
                # Create event in users.events table
                event = form.save(commit=False)
                event.organizer_id = organizer_id
                event.save()
                
                # Create event-specific table in events schema
                event_code = event.event_code
                table_name = f"{event.name.lower().replace(' ', '_')}_{event_code}"
                
                # Create table with all required columns
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS events.{table_name} (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    username VARCHAR(255),
                    user_email VARCHAR(255),
                    num_individuals INTEGER,
                    amount DECIMAL(10,2),
                    paid_status BOOLEAN DEFAULT FALSE,
                    capacity INTEGER,
                    payment_time TIMESTAMP,
                    payment_date DATE,
                    expiration TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TRIGGER update_{table_name}_updated_at
                BEFORE UPDATE ON events.{table_name}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
                """
                
                with connection.cursor() as cursor:
                    cursor.execute(create_table_sql)
                
                messages.success(request, 'Event created successfully!')
                return redirect('organizer:dashboard')
                
            except Exception as e:
                messages.error(request, f'Error creating event: {str(e)}')
                return redirect('organizer:dashboard')
    else:
        form = EventForm()
    
    return render(request, 'organizer/create_event.html', {'form': form})

@login_required(login_url='googlelogin:login_view')
def edit_event(request, event_id):
    if not request.session.get('organizer_id'):
        return redirect('googlelogin:login_view')

    try:
        event = get_object_or_404(Event, id=event_id)
        
        # Check if the event belongs to this organizer
        organizer_id = request.session.get('organizer_id')
        if event.organizer_id != organizer_id and event.organizer_request_id != organizer_id:
            messages.error(request, 'You do not have permission to edit this event')
            return redirect('organizer:event_list')
        
        if request.method == 'POST':
            # Update event
            event.name = request.POST.get('name')
            event.description = request.POST.get('description')
            event.date = request.POST.get('date')
            event.location = request.POST.get('location')
            event.capacity = request.POST.get('capacity')
            event.price = request.POST.get('price')
            
            if request.FILES.get('image'):
                event.image = request.FILES.get('image').read()
            
            event.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('organizer:event_detail', event_id=event.id)

        context = {
            'event': event
        }
        return render(request, 'organizer/edit_event.html', context)

    except Exception as e:
        messages.error(request, f'Error loading event: {str(e)}')
        return redirect('googlelogin:login_view')

@login_required(login_url='googlelogin:login_view')
def notification_list(request):
    if not request.session.get('organizer_id'):
        return redirect('googlelogin:login_view')

    try:
        organizer_id = request.session.get('organizer_id')
        notifications = OrganizerNotification.objects.filter(organizer_id=organizer_id)

        context = {
            'notifications': notifications
        }
        return render(request, 'organizer/notification_list.html', context)

    except Exception as e:
        messages.error(request, f'Error loading notifications: {str(e)}')
        return redirect('googlelogin:login_view')

@login_required(login_url='googlelogin:login_view')
def mark_notification_read(request, notification_id):
    if not request.session.get('organizer_id'):
        return redirect('googlelogin:login_view')

    try:
        organizer_id = request.session.get('organizer_id')
        notification = get_object_or_404(OrganizerNotification, id=notification_id, organizer_id=organizer_id)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})

    except (OrganizerNotification.DoesNotExist, Exception) as e:
        return JsonResponse({'error': 'Not found'}, status=404)

def create_event(request):
    if not request.session.get('organizer_logged_in'):
        messages.error(request, "Please log in to host an event.")
        return redirect('organizer:login')
    
    try:
        if request.method == 'POST':
            # Debug prints
            print("="*50)
            print("All POST data:", request.POST)
            print("POST keys:", list(request.POST.keys()))
            print("="*50)
            
            # Get form data with proper validation
            name = request.POST.get('name', '').strip()
            location = request.POST.get('location', '').strip()
            date = request.POST.get('date', '').strip()
            start_time = request.POST.get('start_time', '').strip()
            end_time = request.POST.get('end_time', '').strip()
            description = request.POST.get('description', '').strip()
            performer = request.POST.get('performer_name', '').strip()
            
            # Handle price with proper null check - convert to integer
            try:
                price_raw = request.POST.get('price')
                print("Price raw value:", price_raw)  # Debug print
                
                if price_raw is None or str(price_raw).strip() == '':
                    price = 0
                    print("Setting default price to 0")  # Debug print
                else:
                    # Remove any non-numeric characters except decimal point
                    price_clean = ''.join(c for c in str(price_raw) if c.isdigit() or c == '.')
                    print("Price after cleaning:", price_clean)  # Debug print
                    
                    if price_clean:
                        price = int(float(price_clean))
                        print("Final price value:", price)  # Debug print
                    else:
                        price = 0
                        print("Setting price to 0 due to no valid numbers")  # Debug print
            except Exception as e:
                print(f"Error converting price: {str(e)}")
                print(f"Price raw value type: {type(price_raw)}")
                print(f"Price raw value: {price_raw}")
                messages.error(request, "Invalid price value. Please enter a whole number.")
                return render(request, 'organizer/create_event.html')
            
            # Handle capacity with proper null check
            try:
                capacity_raw = request.POST.get('capacity', '1')
                if not capacity_raw or str(capacity_raw).strip() == '':
                    capacity = 1
                else:
                    # Remove any non-numeric characters
                    capacity_clean = ''.join(c for c in str(capacity_raw) if c.isdigit())
                    if capacity_clean:
                        capacity = int(capacity_clean)
                    else:
                        capacity = 1
            except Exception as e:
                print(f"Error converting capacity: {str(e)}")
                messages.error(request, "Invalid capacity value")
                return render(request, 'organizer/create_event.html')
            
            # Validate required fields
            if not all([name, location, date, start_time]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'organizer/create_event.html')
            
            # Validate numeric values
            if capacity <= 0:
                messages.error(request, "Capacity must be greater than 0.")
                return render(request, 'organizer/create_event.html')
                
            if price < 0:
                messages.error(request, "Price cannot be negative.")
                return render(request, 'organizer/create_event.html')
            
            # Validate and convert date and time
            try:
                datetime_str = f"{date} {start_time}"
                event_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                if event_datetime <= datetime.now():
                    messages.error(request, "Event date and time must be in the future.")
                    return render(request, 'organizer/create_event.html')
            except ValueError as e:
                print(f"Date/time conversion error: {str(e)}")
                messages.error(request, "Please enter valid date and time.")
                return render(request, 'organizer/create_event.html')
            
            # Generate a unique 6-character event code
            event_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Get organizer ID from session
            organizer_id = request.session.get('organizer_id')
            print(f"Organizer ID from session: {organizer_id}")
            print(f"Session data: {dict(request.session)}")
            
            if not organizer_id:
                messages.error(request, "Invalid organizer session.")
                return redirect('organizer:login')
            
            # Start database transaction
            with connection.cursor() as cursor:
                try:
                    # Begin transaction
                    cursor.execute("BEGIN")
                    
                    # First verify the organizer exists
                    print(f"Executing query to verify organizer with ID: {organizer_id}")
                    
                    # Get organizer email from session as a fallback
                    organizer_email = request.session.get('organizer_email')
                    print(f"Organizer email from session: {organizer_email}")
                    
                    # First check if the organizer exists in the organizers table
                    # This is the table that matters for event creation
                    cursor.execute("""
                        SELECT id, organization_name, email FROM organizers WHERE id = %s
                    """, [organizer_id])
                    
                    org_result = cursor.fetchone()
                    print(f"Query result from organizers table by ID: {org_result}")
                    
                    # If not found by ID, try by email
                    if not org_result and organizer_email:
                        cursor.execute("""
                            SELECT id, organization_name, email FROM organizers WHERE email = %s
                        """, [organizer_email])
                        
                        org_result = cursor.fetchone()
                        print(f"Query result from organizers table by email: {org_result}")
                    
                    # If found in organizers table, use that ID
                    if org_result:
                        organizer_id = org_result[0]
                        print(f"Using organizer ID from organizers table: {organizer_id}")
                        # Update the session with the correct ID
                        request.session['organizer_id'] = organizer_id
                        request.session.save()
                    else:
                        # If not found in organizers table, check if exists in organizer_requests
                        cursor.execute("""
                            SELECT id, organization_name, email FROM users.organizer_requests WHERE id = %s
                        """, [organizer_id])
                        
                        org_req_result = cursor.fetchone()
                        print(f"Query result from users.organizer_requests table by ID: {org_req_result}")
                        
                        # If not found by ID, try by email
                        if not org_req_result and organizer_email:
                            cursor.execute("""
                                SELECT id, organization_name, email FROM users.organizer_requests WHERE email = %s
                            """, [organizer_email])
                            
                            org_req_result = cursor.fetchone()
                            print(f"Query result from users.organizer_requests table by email: {org_req_result}")
                        
                        if org_req_result:
                            # Found in organizer_requests but not in organizers
                            # We need to create an entry in the organizers table
                            print("Found organizer in organizer_requests but not in organizers table")
                            print("Creating entry in organizers table...")
                            
                            # Get the data from organizer_requests
                            org_req_id = org_req_result[0]
                            org_name = org_req_result[1]
                            org_email = org_req_result[2]
                            
                            # Get more details from organizer_requests
                            cursor.execute("""
                                SELECT user_id, username, owner_names, password, address
                                FROM users.organizer_requests WHERE id = %s
                            """, [org_req_id])
                            
                            org_details = cursor.fetchone()
                            
                            if org_details:
                                # Insert into organizers table
                                cursor.execute("""
                                    INSERT INTO organizers 
                                    (user_id, organization_name, username, owner_names, email, password, address, verification_status)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'approved')
                                    RETURNING id
                                """, [org_details[0], org_name, org_details[1], org_details[2], 
                                      org_email, org_details[3], org_details[4]])
                                
                                # Get the new organizer ID
                                new_organizer_id = cursor.fetchone()[0]
                                organizer_id = new_organizer_id
                                print(f"Created new entry in organizers table with ID: {organizer_id}")
                                
                                # Update the session with the correct ID
                                request.session['organizer_id'] = organizer_id
                                request.session.save()
                            else:
                                raise Exception("Could not get organizer details from organizer_requests")
                        else:
                            raise Exception("Invalid organizer ID - not found in any table")
                    
                    # Get current timestamp for created_at and updated_at
                    current_time = timezone.now()
                    
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
                    
                    # Create event-specific table name using the same format as existing tables
                    # Format: eventname_eventcode (all lowercase, spaces replaced with underscores)
                    table_name = f"{name.lower().replace(' ', '_')}_{event_code}"
                    
                    # Create event-specific table in events schema
                    cursor.execute(f"""
                        CREATE TABLE IF NOT EXISTS events.{adapt_identifier(table_name)} (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER,
                            username VARCHAR(255),
                            user_email VARCHAR(255),
                            num_individuals INTEGER,
                            amount INTEGER,
                            paid_status BOOLEAN DEFAULT FALSE,
                            capacity INTEGER,
                            payment_time TIMESTAMP,
                            payment_date DATE,
                            expiration TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Add trigger for updated_at
                    cursor.execute(f"""
                        CREATE OR REPLACE TRIGGER update_{table_name}_updated_at
                        BEFORE UPDATE ON events.{adapt_identifier(table_name)}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                    """)
                    
                    # Commit transaction
                    cursor.execute("COMMIT")
                    messages.success(request, f"Event '{name}' hosted successfully!")
                    return redirect('organizer:dashboard')
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    print(f"Database error: {str(e)}")
                    messages.error(request, f"Error hosting event: {str(e)}")
                    return render(request, 'organizer/create_event.html')
        
        return render(request, 'organizer/create_event.html')
        
    except Exception as e:
        print(f"Unexpected error in host_event view: {str(e)}")
        messages.error(request, "An unexpected error occurred while hosting the event.")
        return render(request, 'organizer/create_event.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # Get the organizer ID
                cursor.execute("""
                    SELECT id FROM users_organizer 
                    WHERE email = %s
                """, [request.user.email])
                organizer = cursor.fetchone()
                
                if organizer:
                    organizer_id = organizer[0]
                    
                    # Delete related events first
                    cursor.execute("""
                        DELETE FROM users_events 
                        WHERE organizer_id = %s
                    """, [organizer_id])
                    
                    # Delete organizer record
                    cursor.execute("""
                        DELETE FROM users_organizer 
                        WHERE id = %s
                    """, [organizer_id])
                    
                    # Delete user account
                    cursor.execute("""
                        DELETE FROM auth_user 
                        WHERE email = %s
                    """, [request.user.email])
                    
                    messages.success(request, 'Your account has been successfully deleted.')
                    return redirect('login')
                else:
                    messages.error(request, 'Organizer account not found.')
                    return redirect('organizer:dashboard')
                    
        except Exception as e:
            messages.error(request, f'An error occurred while deleting your account: {str(e)}')
            return redirect('organizer:dashboard')
            
    return redirect('organizer:dashboard')

@login_required
def profile(request):
    if not request.session.get('organizer_logged_in'):
        messages.error(request, 'Please log in first')
        return redirect('organizer:login')
    
    try:
        # Get organizer from session
        organizer_id = request.session.get('organizer_id')
        if not organizer_id:
            request.session.flush()
            messages.error(request, 'Session expired. Please log in again')
            return redirect('organizer:login')
        
        # Get organizer details with statistics
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT o.*, 
                       COUNT(DISTINCT e.id) as total_events,
                       SUM(CASE WHEN e.is_active = true THEN 1 ELSE 0 END) as active_events,
                       SUM(e.capacity) as total_capacity,
                       SUM(e.price * e.capacity) as potential_revenue
                FROM organizers o
                LEFT JOIN events e ON o.id = e.organizer_id
                WHERE o.id = %s
                GROUP BY o.id
            """, [organizer_id])
            organizer = dictfetchone(cursor)
        
        if not organizer:
            request.session.flush()
            messages.error(request, 'Account not found. Please log in again')
            return redirect('organizer:login')
        
        context = {
            'organizer': organizer,
            'total_events': organizer['total_events'] or 0,
            'active_events': organizer['active_events'] or 0,
            'total_capacity': organizer['total_capacity'] or 0,
            'total_revenue': float(organizer['potential_revenue'] or 0)
        }
        
        return render(request, 'organizer/profile.html', context)
        
    except Exception as e:
        print(f"Profile error: {str(e)}")
        messages.error(request, f'Error loading profile: {str(e)}')
        return redirect('organizer:dashboard')
