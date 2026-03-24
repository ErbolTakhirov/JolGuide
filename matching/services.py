"""
Сервис AI-подбора гидов через Gemini API.
Использует shortlist из SQLite, отправляет в Gemini, разбирает JSON-ответ.
При недоступности Gemini — fallback на рейтинг.
"""
import json
import logging

from django.conf import settings
from accounts.models import GuideProfile

logger = logging.getLogger(__name__)

# Лимит гидов в shortlist для Gemini (экономия токенов)
SHORTLIST_SIZE = 20
TOP_N = 3


def _build_shortlist(prompt: str) -> list[GuideProfile]:
    """Возвращает shortlist гидов для передачи в Gemini."""
    guides = GuideProfile.objects.all().order_by('-rating', '-is_verified')

    # Простая текстовая фильтрация по слову из запроса
    words = [w.lower() for w in prompt.split() if len(w) > 3]
    city_matches = GuideProfile.objects.none()
    for word in words:
        city_matches = city_matches | GuideProfile.objects.filter(city__icontains=word)
        city_matches = city_matches | GuideProfile.objects.filter(languages__icontains=word)
    city_matches = city_matches.distinct().order_by('-rating')

    combined = list(city_matches) + [g for g in guides if g not in list(city_matches)]
    return combined[:SHORTLIST_SIZE]


def _guides_to_context(guides: list[GuideProfile]) -> str:
    """Сериализует гидов в строку для промпта."""
    lines = []
    for g in guides:
        lines.append(
            f"ID:{g.pk} | {g.name} | Город:{g.city} | Языки:{g.languages} "
            f"| Рейтинг:{g.rating} | Цена от:{g.price_from}$ | "
            f"Bio:{g.bio[:200]} | Услуги:{g.services_text[:200]}"
        )
    return "\n".join(lines)


def _fallback_results(shortlist: list[GuideProfile]) -> list[dict]:
    """Возвращает top-3 по рейтингу при недоступности Gemini."""
    top = sorted(shortlist, key=lambda g: (-g.rating, -float(g.price_from or 0)))[:TOP_N]
    return [
        {
            "guide": g,
            "score": max(0.0, g.rating / 5.0),
            "reason": f"{g.name} имеет высокий рейтинг ({g.rating}/5) и работает в {g.city}.",
            "compromise": "Подбор выполнен по рейтингу (AI временно недоступен).",
        }
        for g in top
    ]


def get_ai_matches(prompt: str) -> list[dict]:
    """
    Основная точка входа.
    Возвращает список dict: {guide, score, reason, compromise}.
    """
    shortlist = _build_shortlist(prompt)
    if not shortlist:
        return []

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY не задан — используем fallback.")
        return _fallback_results(shortlist)

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        guide_context = _guides_to_context(shortlist)
        system_prompt = f"""Ты — AI-ассистент платформы JolGit для подбора локальных гидов.

Вот список доступных гидов (формат: ID | Имя | Город | Языки | Рейтинг | Цена | Bio | Услуги):
{guide_context}

Запрос туриста: "{prompt}"

Задача: выбери ровно {TOP_N} наиболее подходящих гидов.
Ответь ТОЛЬКО валидным JSON-массивом (без markdown) вида:
[
  {{"guide_id": 1, "score": 0.95, "reason": "...", "compromise": "..."}},
  {{"guide_id": 2, "score": 0.80, "reason": "...", "compromise": "..."}},
  {{"guide_id": 3, "score": 0.70, "reason": "...", "compromise": "..."}}
]
Где:
- guide_id: ID гида из списка
- score: от 0.0 до 1.0 (насколько подходит)
- reason: 1-2 предложения почему подходит (на русском)
- compromise: 1 предложение о том, что НЕ идеально (на русском)
"""
        response = model.generate_content(system_prompt)
        raw = response.text.strip()

        # Убираем возможный markdown-блок
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        id_to_guide = {g.pk: g for g in shortlist}
        results = []
        for item in data[:TOP_N]:
            guide_id = item.get("guide_id")
            if guide_id and guide_id in id_to_guide:
                results.append({
                    "guide": id_to_guide[guide_id],
                    "score": float(item.get("score", 0.5)),
                    "reason": item.get("reason", ""),
                    "compromise": item.get("compromise", ""),
                })
        return results if results else _fallback_results(shortlist)

    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return _fallback_results(shortlist)
