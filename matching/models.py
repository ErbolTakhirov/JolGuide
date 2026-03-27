from django.db import models
from django.conf import settings
from accounts.models import GuideProfile


class MatchRequest(models.Model):
    """Запрос туриста на AI-подбор гида."""
    tourist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='match_requests',
        verbose_name='Турист',
    )
    prompt = models.TextField('Текст запроса')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Запрос подбора'
        verbose_name_plural = 'Запросы подбора'
        ordering = ['-created_at']

    def __str__(self):
        return f'Match #{self.pk} от {self.tourist}'


class MatchResult(models.Model):
    """Результат AI-подбора: связь гида с запросом."""
    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='Запрос',
    )
    guide = models.ForeignKey(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='match_results',
        verbose_name='Гид',
    )
    score = models.FloatField('Оценка совпадения')
    reason = models.TextField('Обоснование', blank=True)
    compromise = models.TextField('Компромисс', blank=True)

    class Meta:
        verbose_name = 'Результат подбора'
        verbose_name_plural = 'Результаты подбора'
        ordering = ['-score']

    def __str__(self):
        return f'{self.guide.name} — {self.score:.0%}'


# ──────────────────────────────────────────────────
#  AI Chat Travel Assistant — Session Models
# ──────────────────────────────────────────────────

class MatchSession(models.Model):
    """Одна сессия AI-диалога с туристом."""

    STATUS_COLLECTING = 'collecting'
    STATUS_READY = 'ready'
    STATUS_CHOICES = [
        (STATUS_COLLECTING, 'Сбор данных'),
        (STATUS_READY, 'Маршрут готов'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='match_sessions',
    )
    session_key = models.CharField(max_length=64, blank=True)  # для анонимных

    city = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    days = models.PositiveIntegerField(null=True, blank=True)
    budget_total = models.PositiveIntegerField(null=True, blank=True)
    interests = models.TextField(blank=True)
    pace = models.CharField(max_length=30, blank=True)  # relaxed / active
    people_count = models.PositiveIntegerField(default=1)
    with_children = models.BooleanField(default=False)

    status = models.CharField(max_length=30, default=STATUS_COLLECTING, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Сессия чата AI'
        verbose_name_plural = 'Сессии чата AI'
        ordering = ['-created_at']

    def __str__(self):
        return f'Session #{self.pk} ({self.city or "?"} — {self.status})'


class MatchMessage(models.Model):
    """Одно сообщение в AI-чате."""

    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = [
        (ROLE_USER, 'Пользователь'),
        (ROLE_ASSISTANT, 'AI'),
    ]

    session = models.ForeignKey(
        MatchSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение AI-чата'
        verbose_name_plural = 'Сообщения AI-чата'
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] {self.content[:60]}'


class TripPlan(models.Model):
    """Итоговый маршрут поездки, привязанный к сессии."""

    session = models.OneToOneField(
        MatchSession,
        on_delete=models.CASCADE,
        related_name='trip_plan',
    )
    json_result = models.JSONField(default=dict)
    fallback_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Маршрут поездки'
        verbose_name_plural = 'Маршруты поездок'

    def __str__(self):
        return f'TripPlan for Session #{self.session_id}'
