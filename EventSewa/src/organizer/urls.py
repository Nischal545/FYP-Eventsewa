from django.urls import path
from . import views

app_name = 'organizer'

urlpatterns = [
    path('login/', views.organizer_login, name='login'),
    path('logout/', views.organizer_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/', views.event_list, name='event_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:event_id>/deactivate/', views.deactivate_event, name='deactivate_event'),
    path('events/<int:event_id>/activate/', views.activate_event, name='activate_event'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('profile/', views.profile, name='profile'),
]
