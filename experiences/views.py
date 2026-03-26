from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg

from accounts.models import GuideProfile
from .models import Experience, ExperienceBooking, ExperienceReview, GuideFeedbackSummary
from .forms import ExperienceForm, ExperienceReviewForm
from .services import generate_guide_feedback


# ══════════════════════════════════════════════
# PUBLIC VIEWS
# ══════════════════════════════════════════════

def experience_list(request):
    """Каталог экскурсий с фильтрами."""
    experiences = Experience.objects.filter(
        is_active=True,
        guide__is_verified=True,
    ).select_related('guide').order_by('datetime')

    city = request.GET.get('city', '')
    mode = request.GET.get('mode', '')
    category = request.GET.get('category', '')

    if city:
        experiences = experiences.filter(city__icontains=city)
    if mode:
        experiences = experiences.filter(mode=mode)
    if category:
        experiences = experiences.filter(category=category)

    all_cities = (
        Experience.objects.filter(is_active=True)
        .values_list('city', flat=True).distinct().order_by('city')
    )

    context = {
        'experiences': experiences,
        'all_cities': all_cities,
        'current_city': city,
        'current_mode': mode,
        'current_category': category,
        'mode_choices': Experience.Mode.choices,
        'category_choices': Experience.Category.choices,
    }
    return render(request, 'experiences/experience_list.html', context)


def experience_detail(request, exp_id):
    """Детальная страница экскурсии."""
    exp = get_object_or_404(Experience.objects.select_related('guide'), pk=exp_id)
    reviews = ExperienceReview.objects.filter(experience=exp).select_related('tourist')[:10]

    can_review = False
    user_booking = None
    if request.user.is_authenticated:
        user_booking = ExperienceBooking.objects.filter(
            experience=exp, tourist=request.user
        ).first()
        if user_booking and user_booking.status == ExperienceBooking.Status.COMPLETED:
            can_review = not ExperienceReview.objects.filter(booking=user_booking).exists()

    review_form = ExperienceReviewForm() if can_review else None

    context = {
        'exp': exp,
        'reviews': reviews,
        'can_review': can_review,
        'review_form': review_form,
        'user_booking': user_booking,
    }
    return render(request, 'experiences/experience_detail.html', context)


@login_required
def book_experience(request, exp_id):
    """Бронирование / присоединение к экскурсии."""
    exp = get_object_or_404(Experience, pk=exp_id, is_active=True)

    if request.user.role != 'tourist':
        messages.error(request, 'Только туристы могут бронировать экскурсии.')
        return redirect('experiences:detail', exp_id=exp.pk)

    # Check if already booked
    if ExperienceBooking.objects.filter(experience=exp, tourist=request.user).exists():
        messages.warning(request, 'Вы уже забронировали эту экскурсию.')
        return redirect('experiences:detail', exp_id=exp.pk)

    num_guests = 1
    if exp.mode == Experience.Mode.GROUP:
        try:
            num_guests = int(request.POST.get('num_guests', 1))
            num_guests = max(1, num_guests)
        except (ValueError, TypeError):
            num_guests = 1

    # Check capacity
    if exp.seats_left < num_guests:
        messages.error(request, 'Недостаточно мест! Попробуйте меньшее количество.')
        return redirect('experiences:detail', exp_id=exp.pk)

    ExperienceBooking.objects.create(
        experience=exp,
        tourist=request.user,
        num_guests=num_guests,
        status=ExperienceBooking.Status.PENDING,
    )
    messages.success(request, 'Бронирование отправлено! Ожидайте подтверждения от гида.')
    return redirect('experiences:detail', exp_id=exp.pk)


@login_required
def add_experience_review(request, exp_id):
    """Отзыв на экскурсию после завершения."""
    exp = get_object_or_404(Experience, pk=exp_id)
    booking = get_object_or_404(
        ExperienceBooking,
        experience=exp,
        tourist=request.user,
        status=ExperienceBooking.Status.COMPLETED,
    )

    if ExperienceReview.objects.filter(booking=booking).exists():
        messages.warning(request, 'Вы уже оставили отзыв.')
        return redirect('experiences:detail', exp_id=exp.pk)

    if request.method == 'POST':
        form = ExperienceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.experience = exp
            review.guide = exp.guide
            review.tourist = request.user
            review.save()

            # Recalculate guide rating
            _recalc_guide_rating(exp.guide)

            messages.success(request, 'Спасибо за отзыв!')

    return redirect('experiences:detail', exp_id=exp.pk)


def _recalc_guide_rating(guide):
    """Пересчёт среднего рейтинга гида по всем отзывам."""
    from reviews.models import Review
    # Combine old reviews + new experience reviews
    old_avg = Review.objects.filter(guide=guide).aggregate(avg=Avg('rating'))['avg']
    new_avg = ExperienceReview.objects.filter(guide=guide).aggregate(avg=Avg('rating'))['avg']

    ratings = []
    if old_avg:
        old_count = Review.objects.filter(guide=guide).count()
        ratings.extend([old_avg] * old_count)
    if new_avg:
        new_count = ExperienceReview.objects.filter(guide=guide).count()
        ratings.extend([new_avg] * new_count)

    if ratings:
        guide.rating = round(sum(ratings) / len(ratings), 2)
    else:
        guide.rating = 0
    guide.save(update_fields=['rating'])


# ══════════════════════════════════════════════
# GUIDE DASHBOARD VIEWS
# ══════════════════════════════════════════════

@login_required
def guide_dashboard(request):
    """Кабинет гида: экскурсии, бронирования, отзывы, AI-сводка."""
    if request.user.role != 'guide':
        messages.error(request, 'Доступно только для гидов.')
        return redirect('home')

    guide = get_object_or_404(GuideProfile, user=request.user)
    experiences = Experience.objects.filter(guide=guide).order_by('-created_at')
    bookings = ExperienceBooking.objects.filter(
        experience__guide=guide
    ).select_related('experience', 'tourist').order_by('-created_at')[:20]
    reviews = ExperienceReview.objects.filter(guide=guide).select_related(
        'experience', 'tourist'
    ).order_by('-created_at')[:10]

    # Get or generate feedback summary
    try:
        feedback = guide.feedback_summary
    except GuideFeedbackSummary.DoesNotExist:
        feedback = None

    context = {
        'guide': guide,
        'experiences': experiences,
        'bookings': bookings,
        'reviews': reviews,
        'feedback': feedback,
    }
    return render(request, 'experiences/dashboard.html', context)


@login_required
def experience_create(request):
    """Создание новой экскурсии."""
    if request.user.role != 'guide':
        messages.error(request, 'Доступно только для гидов.')
        return redirect('home')

    guide = get_object_or_404(GuideProfile, user=request.user)
    if not guide.is_verified:
        messages.error(request, 'Для создания экскурсий необходимо пройти верификацию.')
        return redirect('guides:verification_submit')

    if request.method == 'POST':
        form = ExperienceForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.guide = guide
            # Enforce max_participants for private
            if exp.mode == Experience.Mode.PRIVATE:
                exp.max_participants = 1
            exp.save()
            messages.success(request, f'Экскурсия «{exp.title}» создана!')
            return redirect('experiences:dashboard')
    else:
        form = ExperienceForm(initial={'city': guide.city})

    return render(request, 'experiences/experience_form.html', {
        'form': form, 'editing': False,
    })


@login_required
def experience_edit(request, exp_id):
    """Редактирование экскурсии."""
    if request.user.role != 'guide':
        return redirect('home')

    guide = get_object_or_404(GuideProfile, user=request.user)
    exp = get_object_or_404(Experience, pk=exp_id, guide=guide)

    if request.method == 'POST':
        form = ExperienceForm(request.POST, instance=exp)
        if form.is_valid():
            exp = form.save(commit=False)
            if exp.mode == Experience.Mode.PRIVATE:
                exp.max_participants = 1
            exp.save()
            messages.success(request, 'Экскурсия обновлена.')
            return redirect('experiences:dashboard')
    else:
        form = ExperienceForm(instance=exp)

    return render(request, 'experiences/experience_form.html', {
        'form': form, 'editing': True, 'exp': exp,
    })


@login_required
def booking_update_status(request, booking_id, new_status):
    """Гид обновляет статус бронирования."""
    booking = get_object_or_404(ExperienceBooking, pk=booking_id)

    if booking.experience.guide.user != request.user:
        messages.error(request, 'Нет прав.')
        return redirect('experiences:dashboard')

    valid = [s[0] for s in ExperienceBooking.Status.choices]
    if new_status not in valid:
        messages.error(request, 'Недопустимый статус.')
        return redirect('experiences:dashboard')

    booking.status = new_status
    booking.save(update_fields=['status'])

    label_map = {
        'confirmed': 'подтверждено',
        'completed': 'завершено',
        'cancelled': 'отменено',
    }
    messages.success(request, f'Бронирование {label_map.get(new_status, new_status)}.')
    return redirect('experiences:dashboard')


@login_required
def generate_feedback(request):
    """Генерация AI-сводки по отзывам."""
    if request.user.role != 'guide':
        return redirect('home')

    guide = get_object_or_404(GuideProfile, user=request.user)
    generate_guide_feedback(guide)
    messages.success(request, 'AI-сводка обновлена!')
    return redirect('experiences:dashboard')
