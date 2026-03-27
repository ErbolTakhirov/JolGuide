from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import GuideProfile
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Review(models.Model):
    """Отзыв туриста о гиде."""
    tourist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Турист',
    )
    guide = models.ForeignKey(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Гид',
    )
    rating = models.PositiveSmallIntegerField(
        'Оценка',
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField('Текст отзыва', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = [('tourist', 'guide')]

    def __str__(self):
        return f'{self.tourist} → {self.guide.name}: {self.rating}★'


# --- Автоматический пересчет рейтинга гида ---

@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_guide_rating_on_review(sender, instance, **kwargs):
    """Вызывается при создании, изменении или удалении отзыва."""
    instance.guide.update_rating()
