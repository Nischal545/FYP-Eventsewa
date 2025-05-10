"""
URL configuration for src project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from googlelogin import views as google_views
from users import views as user_views
from django.views.generic import RedirectView
from admin_panel import views as admin_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
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
    path('accounts/login/', RedirectView.as_view(url='/googlelogin/login/', permanent=True), name='account_login'),
    path('googlelogin/', include('googlelogin.urls', namespace='googlelogin')),
    path('admin/', include('admin_panel.urls', namespace='admin_panel')),
    path('organizer/', include('organizer.urls', namespace='organizer')),
    path('test-email/', google_views.test_email, name='test_email'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
