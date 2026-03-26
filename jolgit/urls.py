"""JolGit URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('guides/', include('guides.urls')),
    path('chats/', include('chats.urls')),
    path('bookings/', include('bookings.urls')),
    path('match/', include('matching.urls')),
    path('reviews/', include('reviews.urls')),
    
    # API endpoints
    path('api/guides/', include('guides.api_urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
