# matching/views.py
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import MatchSession, MatchMessage, TripPlan
from .services import (
    extract_trip_context,
    get_shortlist,
    get_ai_matches,
    get_ai_trip_plan,
    revise_trip_plan,
    get_weather,
)


# ──────────────────────────────────────────────────────────
#  Main chat page
# ──────────────────────────────────────────────────────────

def match_view(request):
    """
    Страница /match/ — чат-интерфейс AI travel-консьержа.
    """
    # Создать или восстановить сессию
    session = None
    if request.user.is_authenticated:
        # Берём последнюю незавершённую сессию или создаём новую
        if request.GET.get('new'):
            session = MatchSession.objects.create(user=request.user)
        else:
            session = (
                MatchSession.objects.filter(user=request.user)
                .order_by('-created_at')
                .first()
            )
            if not session:
                session = MatchSession.objects.create(user=request.user)
    else:
        # Анонимный пользователь — сессия через django session key
        if not request.session.session_key:
            request.session.create()
        sk = request.session.session_key
        if request.GET.get('new'):
            session = MatchSession.objects.create(session_key=sk)
        else:
            session = (
                MatchSession.objects.filter(session_key=sk)
                .order_by('-created_at')
                .first()
            )
            if not session:
                session = MatchSession.objects.create(session_key=sk)

    chat_messages = list(session.messages.order_by('created_at'))
    trip_plan = getattr(session, 'trip_plan', None)

    return render(request, 'matching/match.html', {
        'session': session,
        'chat_messages': chat_messages,
        'trip_plan': trip_plan,
    })


# ──────────────────────────────────────────────────────────
#  AJAX: Send message
# ──────────────────────────────────────────────────────────

@require_POST
def send_message(request):
    """
    AJAX POST /match/send/
    Body: { session_id, content }
    Returns: { reply, guides, trip_plan, weather }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный формат запроса.'}, status=400)

    session_id = body.get('session_id')
    user_content = body.get('content', '').strip()

    if not user_content:
        return JsonResponse({'error': 'Пустое сообщение.'}, status=400)

    # Получаем сессию
    try:
        session = MatchSession.objects.get(pk=session_id)
    except MatchSession.DoesNotExist:
        return JsonResponse({'error': 'Сессия не найдена.'}, status=404)

    # Сохраняем сообщение пользователя
    MatchMessage.objects.create(session=session, role='user', content=user_content)

    # История чата для AI
    history = list(session.messages.order_by('created_at').values('role', 'content'))

    # Шаг 1: Извлечь контекст из диалога
    # Шаг 1: Извлечь контекст из диалога
    ctx = extract_trip_context(history)

    # Шаг 2: Обновляем сессию из контекста
    session.city = ctx.city or ''
    session.days = ctx.days or 1
    session.budget_total = ctx.budget_total
    session.interests = ', '.join(ctx.interests) if ctx.interests else ''
    session.pace = ctx.pace or ''
    session.people_count = ctx.people_count or 1
    session.with_children = ctx.with_children or False
    session.status = 'ready' if ctx.ready else 'collecting'
    session.save()

    # Шаг 3: Подобрать гидов из БД
    query_text = user_content if not ctx.city else f"{ctx.city} {session.interests}"
    matches = get_ai_matches(query_text)

    if not matches:
        reply = "В базе пока нет гидов под ваш запрос. Попробуйте изменить детали поездки."
        MatchMessage.objects.create(session=session, role='assistant', content=reply)
        return JsonResponse({'reply': reply, 'ready': True, 'guides': []})

    # Шаг 4: Построить маршрут
    plan = get_ai_trip_plan(ctx, matches)

    # Сохранить / обновить TripPlan
    TripPlan.objects.update_or_create(
        session=session,
        defaults={
            'json_result': {k: v for k, v in plan.items() if k not in ('guides', 'best_guide', 'weather')},
            'fallback_used': plan.get('fallback', False),
        }
    )

    # Шаг 5: Погода (уже есть в объекте plan)
    weather = plan.get('weather', {})
    if 'weather_advice' in plan:
        weather['advice'] = plan['weather_advice']

    # Шаг 6: Ответ AI в чат
    reply = plan.get('response_text', 'Готово! Маршрут и гиды подобраны.')
    MatchMessage.objects.create(session=session, role='assistant', content=reply)

    # Сериализуем гидов для JSON
    guides_data = _serialize_guides(matches)

    return JsonResponse({
        'reply': reply,
        'ready': True,
        'guides': guides_data,
        'trip_plan': {k: v for k, v in plan.items() if k not in ('guides', 'best_guide', 'weather')},
        'weather': weather,
    })


# ──────────────────────────────────────────────────────────
#  AJAX: Revise plan
# ──────────────────────────────────────────────────────────

@require_POST
def revise_view(request):
    """
    AJAX POST /match/revise/
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат.'}, status=400)

    session_id = body.get('session_id')
    revision = body.get('revision', '').strip()

    try:
        session = MatchSession.objects.get(pk=session_id)
        trip_plan_obj = session.trip_plan
    except (MatchSession.DoesNotExist, TripPlan.DoesNotExist):
        return JsonResponse({'error': 'Сессия или план не найден.'}, status=404)

    # Формируем объект контекста из данных сессии
    from .services import TripContext
    ctx = TripContext(
        city=session.city,
        days=session.days,
        budget_total=session.budget_total,
        interests=session.interests.split(', ') if session.interests else [],
        pace=session.pace,
        people_count=session.people_count,
        with_children=session.with_children
    )

    # Получить обновленный план
    MatchMessage.objects.create(session=session, role='user', content=revision)
    current_plan = trip_plan_obj.json_result
    new_plan = revise_trip_plan(ctx, current_plan, revision)

    trip_plan_obj.json_result = {k: v for k, v in new_plan.items() if k not in ('guides', 'best_guide', 'weather')}
    trip_plan_obj.save()

    reply = new_plan.get('response_text', 'Маршрут обновлён!')
    MatchMessage.objects.create(session=session, role='assistant', content=reply)

    return JsonResponse({
        'reply': reply,
        'trip_plan': {k: v for k, v in new_plan.items() if k not in ('guides', 'best_guide', 'weather')},
    })


# ──────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────

def _serialize_guides(matches: list[dict]) -> list[dict]:
    result = []
    for m in matches:
        g = m['guide']
        result.append({
            'id': g.id,
            'name': g.user.get_full_name() or g.user.username,
            'city': g.city,
            'bio': g.bio[:200] if g.bio else '',
            'rating': float(g.rating) if g.rating else 0,
            'is_verified': g.is_verified,
            'score': round(m['score'], 2),
            'reason': m.get('reason', ''),
        })
    return result
