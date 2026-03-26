from rest_framework import generics
from accounts.models import GuideProfile
from .serializers import GuideSerializer

class GuideListAPIView(generics.ListAPIView):
    """API endpoint for listing guides."""
    serializer_class = GuideSerializer

    def get_queryset(self):
        queryset = GuideProfile.objects.all().order_by('-rating')
        city = self.request.query_params.get('city', None)
        language = self.request.query_params.get('language', None)
        verified = self.request.query_params.get('verified', None)

        if city:
            queryset = queryset.filter(city__icontains=city)
        if language:
            queryset = queryset.filter(languages__icontains=language)
        if verified == '1':
            queryset = queryset.filter(is_verified=True)
            
        return queryset

class GuideDetailAPIView(generics.RetrieveAPIView):
    """API endpoint for retrieving a single guide."""
    queryset = GuideProfile.objects.all()
    serializer_class = GuideSerializer
