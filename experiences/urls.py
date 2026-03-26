from django.urls import path
from . import views

app_name = 'experiences'

urlpatterns = [
    # Public
    path('', views.experience_list, name='list'),
    path('<int:exp_id>/', views.experience_detail, name='detail'),
    path('<int:exp_id>/book/', views.book_experience, name='book'),
    path('<int:exp_id>/review/', views.add_experience_review, name='add_review'),

    # Guide dashboard
    path('dashboard/', views.guide_dashboard, name='dashboard'),
    path('create/', views.experience_create, name='create'),
    path('<int:exp_id>/edit/', views.experience_edit, name='edit'),
    path('booking/<int:booking_id>/<str:new_status>/', views.booking_update_status, name='booking_status'),
    path('dashboard/feedback/', views.generate_feedback, name='generate_feedback'),
]
