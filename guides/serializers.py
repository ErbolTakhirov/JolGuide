from rest_framework import serializers
from accounts.models import GuideProfile

class GuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuideProfile
        fields = [
            'id', 'name', 'photo', 'city', 'languages', 
            'bio', 'services_text', 'price_from', 'rating', 'is_verified'
        ]
