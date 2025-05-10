from django.urls import path
from . import views

app_name = 'googlelogin'  # Define namespace

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('signup/', views.signup, name='signup'),
    path('store_input/', views.store_input, name='store_input'),
    path('verification/', views.verification, name='verification'),
    path('login/', views.login_view, name='login_view'),
    path('direct-login/', views.direct_login, name='direct_login'),
    path('direct-organizer-login/', views.direct_organizer_login, name='direct_organizer_login'),
    path('logout/', views.admin_logout, name='logout_view'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('delete_unverified/', views.delete_unverified, name='delete_unverified'),
    
    # Admin routes
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-users/', views.admin_users_list, name='admin_users_list'),
    path('admin-organizers/', views.admin_organizers_list, name='admin_organizers_list'),
    path('admin-events/', views.admin_events_list, name='admin_events_list'),
    path('admin-event-history/', views.admin_event_history, name='admin_event_history'),
    path('admin-pending-requests/', views.admin_pending_requests, name='admin_pending_requests'),
    path('admin-profile/', views.admin_profile, name='admin_profile'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('manage-user/<int:user_id>/', views.manage_user, name='manage_user'),
    path('manage-organizer/<int:organizer_id>/', views.manage_organizer, name='manage_organizer'),
    path('manage-event/<int:event_id>/', views.manage_event, name='manage_event'),
    path('manage-request/<int:request_id>/', views.manage_request, name='manage_request'),
    
    # Organizer routes
    path('become-organizer/', views.organizer_signup, name='become_organizer'),
    path('organizer-dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('test-email/', views.test_email, name='test_email'),
] 