from django.shortcuts import render
from accounts.models import GuideProfile


def home_view(request):
    """Landing page с demo-гидами."""
    demo_guides = GuideProfile.objects.filter(is_verified=True).order_by('-rating')[:3]
    if not demo_guides.exists():
        demo_guides = GuideProfile.objects.all().order_by('-rating')[:3]
    return render(request, 'home.html', {'demo_guides': demo_guides})
