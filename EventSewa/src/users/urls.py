# users/urls.py
from django.contrib.auth.decorators import login_required
from django.urls import path
from . import views

app_name = 'users'  # Define namespace

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),  # Adding explicit home path
    path('profile/', views.profile, name='profile'),
    path('history/', views.history, name='history'),
    path('organizer-signup/', views.organizer_signup, name='organizer_signup'),
    # Redirecting search to dashboard
    path('search/', views.dashboard, name='search'),
    path('buy-ticket/<int:event_id>/', views.buy_ticket, name='buy_ticket'),
    path('event-details/<int:event_id>/', views.event_details, name='event_details'),
    path('host-event/', views.host_event, name='host_event'),
    path('payment/', views.payment, name='payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failure/', views.payment_failure, name='payment_failure'),
    path('settings/', views.settings, name='settings'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/notifications/', views.update_notifications, name='update_notifications'),
    path('settings/privacy/', views.update_privacy, name='update_privacy'),
    path('settings/account/', views.account_settings, name='account_settings'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('dashboard/', views.dashboard, name='dashboard'),
]