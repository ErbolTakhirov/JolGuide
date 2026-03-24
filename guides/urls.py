from django.urls import path
from . import views

app_name = 'guides'

urlpatterns = [
    path('', views.guide_list, name='list'),
    path('<int:guide_id>/', views.guide_detail, name='detail'),
]
