from django.urls import path
from . import views

app_name = 'chats'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('<int:user_id>/', views.chat_room, name='room'),
]
