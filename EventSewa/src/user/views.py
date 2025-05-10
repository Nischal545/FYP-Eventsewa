from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.utils import timezone
from django.contrib import messages

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@login_required
def dashboard(request):
    try:
        # Get user's tickets and events
        with connection.cursor() as cursor:
            # Get total tickets and amount spent
            cursor.execute("""
                SELECT COUNT(*) as total_tickets, SUM(amount) as total_spent
                FROM event_tickets
                WHERE user_id = %s
            """, [request.user.id])
            stats = dictfetchone(cursor)
            
            # Get all events
            cursor.execute("""
                SELECT e.*, 
                       COUNT(t.id) as tickets_sold,
                       SUM(t.amount) as total_revenue
                FROM events e
                LEFT JOIN event_tickets t ON e.id = t.event_id
                WHERE e.date >= %s
                GROUP BY e.id
                ORDER BY e.date ASC
            """, [timezone.now().date()])
            events = dictfetchall(cursor)
        
        context = {
            'user': request.user,
            'total_tickets': stats['total_tickets'] or 0,
            'total_spent': stats['total_spent'] or 0,
            'events': events,
            'now': timezone.now()
        }
        
        return render(request, 'user/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return redirect('user:login') 