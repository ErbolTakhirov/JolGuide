"""
AI-сводка отзывов для гидов.
Использует DeepSeek API, при недоступности — детерминированный fallback.
"""
import json
import logging
from collections import Counter

from django.conf import settings

from .models import ExperienceReview, GuideFeedbackSummary

logger = logging.getLogger(__name__)


def _collect_reviews(guide):
    """Собирает тексты отзывов для гида."""
    reviews = ExperienceReview.objects.filter(guide=guide).order_by('-created_at')[:50]
    return list(reviews.values_list('rating', 'text'))


def _fallback_summary(review_data):
    """Детерминированная сводка без AI."""
    if not review_data:
        return "Пока недостаточно отзывов для формирования сводки."

    ratings = [r[0] for r in review_data]
    texts = [r[1] for r in review_data if r[1].strip()]
    avg = sum(ratings) / len(ratings)

    positive_keywords = Counter()
    negative_keywords = Counter()

    positive_words = ['отлично', 'супер', 'здорово', 'интересно', 'рекомендую',
                      'понравилось', 'прекрасно', 'замечательно', 'вкусно', 'круто',
                      'великолепно', 'профессионал', 'комфортно', 'классно', 'удобно']
    negative_words = ['плохо', 'скучно', 'дорого', 'опоздал', 'грубо',
                      'разочарован', 'не понравилось', 'холодно', 'неудобно',
                      'долго', 'грязно', 'опоздание']

    for text in texts:
        lower = text.lower()
        for w in positive_words:
            if w in lower:
                positive_keywords[w] += 1
        for w in negative_words:
            if w in lower:
                negative_keywords[w] += 1

    high = [r for r in review_data if r[0] >= 4]
    low = [r for r in review_data if r[0] <= 2]

    lines = []
    lines.append("📊 **Что нравится туристам:**")
    if positive_keywords:
        for word, cnt in positive_keywords.most_common(3):
            lines.append(f"- «{word}» (упоминается {cnt} раз)")
    elif len(high) > 0:
        lines.append(f"- {len(high)} из {len(review_data)} туристов поставили 4-5 звёзд")
    else:
        lines.append("- Пока мало данных для анализа")

    lines.append("")
    lines.append("⚠️ **Что можно улучшить:**")
    if negative_keywords:
        for word, cnt in negative_keywords.most_common(3):
            lines.append(f"- «{word}» (упоминается {cnt} раз)")
    elif len(low) > 0:
        lines.append(f"- {len(low)} из {len(review_data)} туристов поставили 1-2 звезды")
    else:
        lines.append("- Серьёзных замечаний не обнаружено")

    lines.append("")
    lines.append("💡 **Рекомендации:**")
    if avg >= 4.0:
        lines.append("- Продолжайте в том же духе! Высокий рейтинг привлекает новых клиентов")
        lines.append("- Попросите довольных туристов оставлять развёрнутые отзывы")
    elif avg >= 3.0:
        lines.append("- Обратите внимание на повторяющиеся замечания")
        lines.append("- Попробуйте улучшить коммуникацию с туристами перед экскурсией")
    else:
        lines.append("- Рекомендуем пересмотреть формат экскурсий")
        lines.append("- Обратите внимание на пунктуальность и подготовку")
    lines.append(f"- Средний рейтинг: {avg:.1f}/5 ({len(review_data)} отзывов)")

    return "\n".join(lines)


def _deepseek_summary(review_data):
    """Генерация сводки через DeepSeek API."""
    import requests

    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
    if not api_key:
        return None

    reviews_text = "\n".join([
        f"Оценка: {r[0]}/5. Отзыв: {r[1]}" for r in review_data if r[1].strip()
    ])
    if not reviews_text:
        reviews_text = "\n".join([f"Оценка: {r[0]}/5 (без текста)" for r in review_data])

    prompt = f"""Ты — AI-ассистент платформы JolGit. Проанализируй отзывы туристов о гиде и составь краткую сводку.

Отзывы:
{reviews_text}

Ответь на русском в следующем формате:

📊 Что нравится туристам:
- ...
- ...

⚠️ Что можно улучшить:
- ...
- ...

💡 Рекомендации:
- ...
- ...
- ...

Будь конкретным и полезным. Не более 10 пунктов всего."""

    try:
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 800,
                'temperature': 0.7,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as exc:
        logger.error("DeepSeek API error: %s", exc)
        return None


def generate_guide_feedback(guide):
    """
    Генерирует AI-сводку отзывов для гида.
    Пробует DeepSeek API, при неудаче — fallback.
    """
    review_data = _collect_reviews(guide)

    if not review_data:
        summary_text = "Пока нет отзывов для анализа. Сводка будет доступна после первых отзывов."
    else:
        # Try DeepSeek first
        summary_text = _deepseek_summary(review_data)
        if not summary_text:
            summary_text = _fallback_summary(review_data)

    obj, created = GuideFeedbackSummary.objects.update_or_create(
        guide=guide,
        defaults={
            'summary_text': summary_text,
            'source_review_count': len(review_data),
        },
    )
    return obj
