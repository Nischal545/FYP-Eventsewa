from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from googlelogin import views as google_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', google_views.landing_page, name='landing_page'),
    path('signup/', google_views.signup, name='signup'),
    path('store_input/', google_views.store_input, name='store_input'),
    path('verification/', google_views.verification, name='verification'),
    path('login/', google_views.login_view, name='login'),
    path('direct-login/', google_views.direct_login, name='direct_login'),
    path('direct-organizer-login/', google_views.direct_organizer_login, name='direct_organizer_login'),
    path('logout/', google_views.admin_logout, name='logout'),
    path('forgot_password/', google_views.forgot_password, name='forgot_password'),
    path('delete_unverified', google_views.delete_unverified, name='delete_unverified'),
    path('users/', include('users.urls')),
    path('googlelogin/', include('googlelogin.urls')),
    path('organizer/', include('organizer.urls')),
    path('events/', include('events.urls')),
    path('admin-panel/', include('admin_panel.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Add this at the end of the file
handler404 = 'googlelogin.views.handler404'
handler500 = 'googlelogin.views.handler500' 