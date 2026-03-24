from django.urls import path
from . import views

app_name = 'matching'

urlpatterns = [
    path('', views.match_view, name='match'),
]
