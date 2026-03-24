from django.shortcuts import render, get_object_or_404
from accounts.models import GuideProfile
from reviews.models import Review


def guide_list(request):
    """Каталог гидов с фильтрами по city, language, is_verified."""
    guides = GuideProfile.objects.all().order_by('-rating')

    # Получаем параметры фильтров
    city = request.GET.get('city', '')
    language = request.GET.get('language', '')
    verified = request.GET.get('verified', '')

    if city:
        guides = guides.filter(city__icontains=city)
    if language:
        guides = guides.filter(languages__icontains=language)
    if verified == '1':
        guides = guides.filter(is_verified=True)

    # Уникальные значения для фильтров
    all_cities = (
        GuideProfile.objects.values_list('city', flat=True)
        .distinct()
        .order_by('city')
    )

    context = {
        'guides': guides,
        'all_cities': all_cities,
        'current_city': city,
        'current_language': language,
        'current_verified': verified,
    }
    return render(request, 'guides/guide_list.html', context)


def guide_detail(request, guide_id):
    """Профиль гида с отзывами."""
    guide = get_object_or_404(GuideProfile, pk=guide_id)
    reviews = Review.objects.filter(guide=guide).select_related('tourist')
    reviews_count = reviews.count()

    context = {
        'guide': guide,
        'reviews': reviews,
        'reviews_count': reviews_count,
    }
    return render(request, 'guides/guide_detail.html', context)
