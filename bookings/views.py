from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import functools

def role_required(role):
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role != role:
                return redirect('home')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

from accounts.models import GuideProfile
from chats.models import ChatMessage
from .models import BookingRequest


@login_required
@role_required('tourist')
def booking_create(request, guide_id):
    """Создание заявки на бронирование гида (только для туристов)."""
    guide = get_object_or_404(GuideProfile, pk=guide_id)

    if request.method == 'POST':
        service_name = request.POST.get('service_name', '').strip()
        date = request.POST.get('date', '')
        comment = request.POST.get('comment', '').strip()

        if service_name and date:
            BookingRequest.objects.create(
                tourist=request.user,
                guide=guide,
                service_name=service_name,
                date=date,
                comment=comment,
            )
            messages.success(request, 'Заявка успешно отправлена! Ожидайте ответа гида.')
            return redirect('bookings:tourist_dashboard')
        else:
            messages.error(request, 'Заполните поля «Услуга» и «Дата».')

    return render(request, 'bookings/create.html', {'guide': guide})


@login_required
@role_required('tourist')
def tourist_dashboard(request):
    """Кабинет туриста: все его заявки."""
    bookings = (
        BookingRequest.objects.filter(tourist=request.user)
        .select_related('guide')
        .order_by('-created_at')
    )
    return render(request, 'bookings/tourist_dashboard.html', {'bookings': bookings})


@login_required
@role_required('guide')
def guide_dashboard(request):
    """Кабинет гида: заявки на его профиль."""
    guide_profile = get_object_or_404(GuideProfile, user=request.user)
    bookings = (
        BookingRequest.objects.filter(guide=guide_profile)
        .select_related('tourist')
        .order_by('-created_at')
    )
    return render(request, 'bookings/guide_dashboard.html', {
        'bookings': bookings,
        'guide': guide_profile,
    })


@login_required
@role_required('guide')
def booking_update_status(request, booking_id, new_status):
    """Гид принимает или отклоняет заявку."""
    booking = get_object_or_404(BookingRequest, pk=booking_id)

    # Только гид, которому принадлежит заявка, может менять статус
    if booking.guide.user != request.user:
        raise PermissionDenied

    if new_status not in (BookingRequest.Status.ACCEPTED, BookingRequest.Status.DECLINED):
        messages.error(request, 'Недопустимый статус.')
        return redirect('bookings:guide_dashboard')

    booking.status = new_status
    booking.save(update_fields=['status'])

    # При принятии заявки — автоматическое сообщение от гида
    if new_status == BookingRequest.Status.ACCEPTED:
        ChatMessage.objects.create(
            sender=booking.guide.user,
            receiver=booking.tourist,
            text=f"Здравствуйте! Ваша заявка на «{booking.service_name}» ({booking.date}) принята. Давайте обсудим детали!"
        )

    label = 'принята' if new_status == BookingRequest.Status.ACCEPTED else 'отклонена'
    messages.success(request, f'Заявка {label}.')
    return redirect('bookings:guide_dashboard')
