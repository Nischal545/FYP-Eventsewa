from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('profile/', views.admin_profile, name='admin_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Admin Event Checker routes
    path('event-check/', views.admin_event_check, name='event_check'),
    path('event-history/', views.admin_event_history, name='event_history'),
    path('update-event-status/<int:event_id>/', views.update_event_status, name='update_event_status'),
    
    # Admin U/O Checker routes
    path('users/', views.admin_users_list, name='users_list'),
    path('users/verify/<int:user_id>/', views.verify_user, name='verify_user'),
    path('organizers/', views.admin_organizers_list, name='organizers_list'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('delete-organizer/<int:organizer_id>/', views.delete_organizer, name='delete_organizer'),
    
    # Admin Request Checker routes
    path('pending-requests/', views.admin_pending_requests, name='pending_requests'),
    path('approve-organizer/<int:request_id>/', views.approve_organizer, name='approve_organizer'),
    path('reject-organizer/<int:request_id>/', views.reject_organizer, name='reject_organizer'),
    
    # API endpoints
    path('get-event-details/<int:event_id>/', views.get_event_details, name='get_event_details'),
] 