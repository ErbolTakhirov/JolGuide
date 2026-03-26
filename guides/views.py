from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import GuideProfile
from reviews.models import Review
from .models import GuideVerificationRequest, GuideReport
from .forms import VerificationRequestForm, GuideReportForm


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
    """Профиль гида с отзывами, бейджем верификации и формой жалобы."""
    guide = get_object_or_404(GuideProfile, pk=guide_id)
    reviews_qs = Review.objects.filter(guide=guide).select_related('tourist')
    reviews_count = reviews_qs.count()

    # Verification status for trust badge
    verification = getattr(guide, 'verification_request', None)
    try:
        verification = guide.verification_request
    except GuideVerificationRequest.DoesNotExist:
        verification = None

    can_review = False
    has_reviewed = False
    if request.user.is_authenticated:
        from bookings.models import BookingRequest
        has_reviewed = reviews_qs.filter(tourist=request.user).exists()
        can_review = (
            request.user.role == 'tourist'
            and not has_reviewed
            and BookingRequest.objects.filter(
                tourist=request.user,
                guide=guide,
                status=BookingRequest.Status.ACCEPTED,
            ).exists()
        )

    report_form = GuideReportForm()

    context = {
        'guide': guide,
        'reviews': reviews_qs,
        'reviews_count': reviews_count,
        'can_review': can_review,
        'has_reviewed': has_reviewed,
        'verification': verification,
        'report_form': report_form,
    }
    return render(request, 'guides/guide_detail.html', context)


@login_required
def verification_submit(request):
    """Подача заявки на верификацию (только для гидов)."""
    if request.user.role != 'guide':
        messages.error(request, 'Только гиды могут подать заявку на верификацию.')
        return redirect('home')

    guide_profile = get_object_or_404(GuideProfile, user=request.user)

    # Check if already has a request
    try:
        existing = guide_profile.verification_request
        if existing.status != GuideVerificationRequest.Status.REJECTED:
            return redirect('guides:verification_status')
        # If rejected, allow resubmission — delete old request
        existing.delete()
    except GuideVerificationRequest.DoesNotExist:
        pass

    if request.method == 'POST':
        form = VerificationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            vr = form.save(commit=False)
            vr.guide = guide_profile
            vr.status = GuideVerificationRequest.Status.SUBMITTED
            vr.save()
            messages.success(request, 'Заявка на верификацию успешно отправлена!')
            return redirect('guides:verification_status')
    else:
        # Pre-fill from existing GuideProfile
        form = VerificationRequestForm(initial={
            'display_name': guide_profile.name,
            'city': guide_profile.city,
            'languages': guide_profile.languages,
            'bio': guide_profile.bio,
            'service_types': guide_profile.services_text,
        })

    return render(request, 'guides/verification_form.html', {
        'form': form,
        'guide': guide_profile,
    })


@login_required
def verification_status(request):
    """Статус верификации для гида."""
    if request.user.role != 'guide':
        messages.error(request, 'Только гиды могут видеть статус верификации.')
        return redirect('home')

    guide_profile = get_object_or_404(GuideProfile, user=request.user)

    try:
        verification = guide_profile.verification_request
    except GuideVerificationRequest.DoesNotExist:
        verification = None

    return render(request, 'guides/verification_status.html', {
        'verification': verification,
        'guide': guide_profile,
    })


@login_required
def report_guide(request, guide_id):
    """Отправка жалобы на гида."""
    guide = get_object_or_404(GuideProfile, pk=guide_id)

    if request.method == 'POST':
        form = GuideReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.guide = guide
            report.reported_by = request.user
            report.save()
            messages.success(request, 'Жалоба отправлена. Спасибо за обратную связь!')
            return redirect('guides:detail', guide_id=guide.pk)

    return redirect('guides:detail', guide_id=guide.pk)
