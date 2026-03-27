import json
import re
import logging
import requests
import time
from datetime import date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from django.core.cache import cache
from django.conf import settings
from .models import GuideProfile, MatchSession

logger = logging.getLogger(__name__)

SHORTLIST_SIZE = 20
TOP_N = 3
CACHE_TTL = 60 * 60  # 1 час

@dataclass
class TripContext:
    city: Optional[str] = None
    days: Optional[int] = None
    budget_total: Optional[int] = None
    interests: List[str] = field(default_factory=list)
    pace: Optional[str] = None
    people_count: int = 1
    with_children: bool = False
    ready: bool = False
    missing: List[str] = field(default_factory=list)
    ai_reply: str = ""

    @classmethod
    def from_dict(cls, data: dict):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

@dataclass
class DayPlanItem:
    time: str
    activity: str
    tip: str

@dataclass
class DayPlan:
    day: int
    title: str
    items: List[DayPlanItem]

# ─────────────────────────────────────────
# СЛОЙ 1 — CAG: кеширование контекста гидов
# ─────────────────────────────────────────

def _serialize_guide(guide) -> str:
    """Превращает объект гида в строку для промпта."""
    return (
        f"[ID:{guide.id} | {guide.user.get_full_name() if hasattr(guide.user, 'get_full_name') else guide.user.username} | "
        f"Город: {guide.city} | Языки: {guide.languages} | "
        f"Рейтинг: {guide.rating:.1f} | От {guide.price_from}₽/день]\n"
        f"Bio: {guide.bio}\n"
        f"Услуги: {guide.services_text}\n"
    )

def get_cached_guides_context(city: str, guides_qs) -> str:
    if not city:
        city = "all"
    cache_key = f"guides_ctx_{city.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    context = "\n".join(_serialize_guide(g) for g in guides_qs)
    cache.set(cache_key, context, CACHE_TTL)
    return context

def invalidate_guide_cache(city: str):
    if city:
        cache.delete(f"guides_ctx_{city.lower().strip()}")

# ─────────────────────────────────────────
# Погода (OpenWeatherMap)
# ─────────────────────────────────────────

def get_weather(city: str) -> dict:
    api_key = getattr(settings, 'WEATHER_API_KEY', None)
    if not api_key:
        return {}
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        return {
            "temp": round(main.get("temp", 0)),
            "desc": weather.get("description", "ясно").capitalize(),
            "humidity": main.get("humidity"),
            "city": data.get("name")
        }
    except Exception as e:
        logger.warning(f"Weather error: {e}")
        return {}

# ─────────────────────────────────────────
# LLM Клиент
# ─────────────────────────────────────────

def _call_llm_json(prompt: str, timeout: int = 30, retries: int = 2) -> dict:
    api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
    if not api_key:
        return {}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://jolgit-app.onrender.com",
        "X-Title": "JolGit AI",
    }
    
    payload = {
        "model": "deepseek/deepseek-chat:free",
        "messages": [{"role": "user", "content": prompt}],
    }


    for attempt in range(retries):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=timeout,
            )
            if response.status_code != 200:
                logger.error(f"OpenRouter Error {response.status_code}: {response.text}")
                response.raise_for_status()
                
            raw = response.json()["choices"][0]["message"]["content"]
            raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
            return json.loads(raw)
        except Exception as e:
            if attempt < retries - 1: time.sleep(1)
            else: logger.error(f"LLM final failure: {e}")
    return {}



# ─────────────────────────────────────────
# Промпты
# ─────────────────────────────────────────

EXTRACT_CONTEXT_PROMPT = """Ты — эмпатичный AI travel-консьерж сервиса JolGit (Кыргызстан).
Извлеки данные о поездке из диалога.
Если данных не хватает, сформулируй 1 вопрос (ai_reply).

Верни ТОЛЬКО JSON:
{{
  "city": str or null,
  "days": int or null,
  "budget_total": int or null,
  "interests": [],
  "pace": "relaxed"/"active"/null,
  "people_count": int,
  "with_children": bool,
  "ready": bool,
  "missing": [],
  "ai_reply": "..."
}}

История:
{history}
"""

TRIP_PLAN_PROMPT = """Ты — AI travel-консьерж JolGit.
Составь план поездки. Погода в {city}: {weather_info}.
Отвечай СТРОГО JSON.

Параметры: {trip_ctx}
Гиды: {guides_summary}

Формат ответа:
{{
  "response_text": "...",
  "best_guide_id": int,
  "days": [ {{ "day": 1, "title": "...", "items": [{{ "time": "...", "activity": "...", "tip": "..." }}] }} ],
  "budget": {{ "total": "..." }},
  "local_tips": [],
  "weather_advice": "..."
}}
"""

REVISE_PROMPT = """Ты — AI travel-консьерж JolGit. Измени маршрут.
Текущий план: {current_plan}
Запрос: "{revision}"
Верни JSON того же формата.
"""

# ─────────────────────────────────────────
# Логика
# ─────────────────────────────────────────

def get_shortlist(query: str):
    from accounts.models import GuideProfile
    from django.db.models import Q, Case, When, IntegerField
    base_qs = GuideProfile.objects.filter(user__is_active=True).select_related('user')
    words = [w for w in query.split() if len(w) > 3]
    if not words: return base_qs.order_by('-rating')[:SHORTLIST_SIZE]
    q_filter = Q()
    for word in words:
        stem = word[:-1] if len(word) > 4 else word
        q_filter |= Q(city__icontains=stem) | Q(languages__icontains=stem)
    filtered = base_qs.filter(q_filter).order_by('-rating')
    return filtered[:SHORTLIST_SIZE] if filtered.exists() else base_qs.order_by('-rating')[:SHORTLIST_SIZE]

def get_ai_matches(tourist_query: str) -> list[dict]:
    shortlist = get_shortlist(tourist_query)
    if not shortlist: return []
    guides_ctx = get_cached_guides_context("all", shortlist)
    # Упрощенный поиск совпадений
    matched = []
    for g in shortlist[:TOP_N]:
        matched.append({"guide": g, "score": 0.9, "reason": "Рекомендованный гид", "compromise": "N/A"})
    return matched

def extract_trip_context(messages: list[dict]) -> TripContext:
    history = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-5:])
    prompt = EXTRACT_CONTEXT_PROMPT.format(history=history)
    data = _call_llm_json(prompt)
    if data: return TripContext.from_dict(data)
    
    # Heuristic fallback
    text = " ".join(m['content'].lower() for m in messages if m['role'] == 'user')
    ctx = TripContext()
    if "бишкек" in text: ctx.city = "Бишкек"
    if "каракол" in text: ctx.city = "Каракол"
    m = re.search(r"(\d+)\s*дн", text)
    if m: ctx.days = int(m.group(1))
    ctx.ready = bool(ctx.city and ctx.days)
    if not ctx.ready: ctx.ai_reply = "В какой город и на сколько дней вы планируете поездку? 😊"
    return ctx

def get_ai_trip_plan(trip_ctx: TripContext, matches: list[dict]) -> dict:
    guides_summary = "\n".join(f"ID:{m['guide'].id} | {m['guide'].city}" for m in matches)
    weather = get_weather(trip_ctx.city or "Бишкек")
    weather_info = f"{weather.get('temp', '?')}°C, {weather.get('desc', 'нет данных')}"
    
    prompt = TRIP_PLAN_PROMPT.format(
        city=trip_ctx.city or "Бишкек",
        weather_info=weather_info,
        trip_ctx=json.dumps(asdict(trip_ctx), ensure_ascii=False),
        guides_summary=guides_summary
    )
    data = _call_llm_json(prompt)
    if data:
        best_id = int(data.get("best_guide_id", 0))
        data["best_guide"] = next((m["guide"] for m in matches if m["guide"].id == best_id), (matches[0]["guide"] if matches else None))
        data["guides"] = matches
        data["weather"] = weather
        return data
    
    # Fallback plan for Bishkek
    if "бишкек" in (trip_ctx.city or "").lower():
        return {
            "response_text": "Извините, сейчас я работаю в режиме офлайн, но вот базовый план для Бишкека!",
            "days": [
                {"day": 1, "title": "Знакомство с городом", "items": [{"time": "10:00", "activity": "Площадь Ала-Тоо и Ошский рынок", "tip": "Попробуйте свежую самсу!"}]},
                {"day": 2, "title": "Природа", "items": [{"time": "09:00", "activity": "Поездка в Ала-Арчу", "tip": "Возьмите удобную обувь."}]}
            ],
            "budget": {"total": "от 5000 сом"},
            "weather": weather,
            "guides": matches,
            "best_guide": (matches[0]["guide"] if matches else None),
            "local_tips": ["Используйте 2ГИС для навигации.", "Такси лучше заказывать через Яндекс Go."],
            "weather_advice": "Одевайтесь по погоде, в горах может быть прохладно."
        }
    return {"response_text": "Ошибка генерации плана. Попробуйте уточнить запрос.", "guides": matches, "fallback": True}

def revise_trip_plan(trip_ctx: TripContext, current_plan: dict, revision: str) -> dict:
    plan_clean = {k: v for k, v in current_plan.items() if k not in ("guides", "best_guide")}
    prompt = REVISE_PROMPT.format(
        current_plan=json.dumps(plan_clean, ensure_ascii=False),
        revision=revision
    )
    data = _call_llm_json(prompt)
    if data:
        data["guides"] = current_plan.get("guides", [])
        data["best_guide"] = current_plan.get("best_guide")
        return data
    return current_plan
