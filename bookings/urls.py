from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('<int:guide_id>/', views.booking_create, name='create'),
    path('my/', views.tourist_dashboard, name='tourist_dashboard'),
    path('guide/', views.guide_dashboard, name='guide_dashboard'),
    path('<int:booking_id>/status/<str:new_status>/', views.booking_update_status, name='update_status'),
]
