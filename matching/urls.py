from django.urls import path
from . import views

app_name = 'matching'

urlpatterns = [
    path('', views.match_view, name='match'),
    path('send/', views.send_message, name='send_message'),
    path('revise/', views.revise_view, name='revise'),
]
