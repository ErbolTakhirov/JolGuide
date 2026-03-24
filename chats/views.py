from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Max

from .models import ChatMessage

User = get_user_model()


@login_required
def inbox(request):
    """Список всех диалогов текущего пользователя."""
    # Все пользователи, с которыми есть переписка
    sent_to = (
        ChatMessage.objects.filter(sender=request.user)
        .values_list('receiver_id', flat=True)
        .distinct()
    )
    received_from = (
        ChatMessage.objects.filter(receiver=request.user)
        .values_list('sender_id', flat=True)
        .distinct()
    )
    partner_ids = set(sent_to) | set(received_from)
    partners = User.objects.filter(pk__in=partner_ids)

    # Для каждого — последнее сообщение
    conversations = []
    for partner in partners:
        last_msg = (
            ChatMessage.objects.filter(
                Q(sender=request.user, receiver=partner) |
                Q(sender=partner, receiver=request.user)
            )
            .order_by('-created_at')
            .first()
        )
        conversations.append({'partner': partner, 'last_msg': last_msg})

    # Сортируем по дате последнего сообщения
    conversations.sort(key=lambda x: x['last_msg'].created_at, reverse=True)

    return render(request, 'chats/inbox.html', {'conversations': conversations})


@login_required
def chat_room(request, user_id):
    """Чат-комната между текущим пользователем и другим пользователем."""
    other_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=other_user,
                text=text,
            )
        # PRG — redirect after POST чтобы F5 не дублировал
        return redirect('chats:room', user_id=user_id)

    chat_messages = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('created_at')

    return render(request, 'chats/room.html', {
        'other_user': other_user,
        'chat_messages': chat_messages,
    })
