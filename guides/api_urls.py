from django.urls import path
from . import api_views

app_name = 'api_guides'

urlpatterns = [
    path('', api_views.GuideListAPIView.as_view(), name='api-list'),
    path('<int:pk>/', api_views.GuideDetailAPIView.as_view(), name='api-detail'),
]
