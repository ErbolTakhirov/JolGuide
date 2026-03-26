from django.urls import path
from . import views

app_name = 'guides'

urlpatterns = [
    path('', views.guide_list, name='list'),
    path('verification/', views.verification_submit, name='verification_submit'),
    path('verification/status/', views.verification_status, name='verification_status'),
    path('<int:guide_id>/', views.guide_detail, name='detail'),
    path('<int:guide_id>/report/', views.report_guide, name='report_guide'),
]
