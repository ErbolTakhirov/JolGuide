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
