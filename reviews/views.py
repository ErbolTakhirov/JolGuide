from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg

from accounts.models import GuideProfile
from bookings.models import BookingRequest
from .models import Review


def _can_review(user, guide):
    """Турист может оставить отзыв только если есть принятая заявка."""
    if not user.is_authenticated:
        return False
    if user.role != 'tourist':
        return False
    return BookingRequest.objects.filter(
        tourist=user,
        guide=guide,
        status=BookingRequest.Status.ACCEPTED,
    ).exists()


def _has_reviewed(user, guide):
    """Проверяем: уже оставлял ли отзыв."""
    return Review.objects.filter(tourist=user, guide=guide).exists()


def _recalc_rating(guide):
    """Пересчитываем средний рейтинг гида."""
    result = Review.objects.filter(guide=guide).aggregate(avg=Avg('rating'))
    guide.rating = round(result['avg'] or 0.0, 2)
    guide.save(update_fields=['rating'])


@login_required
def add_review(request, guide_id):
    """Добавление отзыва от туриста."""
    guide = get_object_or_404(GuideProfile, pk=guide_id)

    if not _can_review(request.user, guide):
        messages.error(request, 'Оставить отзыв можно только после принятой заявки.')
        return redirect('guides:detail', guide_id=guide_id)

    if _has_reviewed(request.user, guide):
        messages.warning(request, 'Вы уже оставляли отзыв для этого гида.')
        return redirect('guides:detail', guide_id=guide_id)

    if request.method == 'POST':
        rating_str = request.POST.get('rating', '')
        text = request.POST.get('text', '').strip()

        if not rating_str.isdigit() or not (1 <= int(rating_str) <= 5):
            messages.error(request, 'Выберите оценку от 1 до 5.')
            return redirect('guides:detail', guide_id=guide_id)

        Review.objects.create(
            tourist=request.user,
            guide=guide,
            rating=int(rating_str),
            text=text,
        )
        _recalc_rating(guide)
        messages.success(request, 'Спасибо за ваш отзыв!')

    return redirect('guides:detail', guide_id=guide_id)
