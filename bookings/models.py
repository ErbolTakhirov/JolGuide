from django.db import models
from django.conf import settings
from accounts.models import GuideProfile


class BookingRequest(models.Model):
    """Заявка на бронирование гида."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'В ожидании'
        ACCEPTED = 'accepted', 'Принята'
        DECLINED = 'declined', 'Отклонена'

    tourist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Турист',
    )
    guide = models.ForeignKey(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Гид',
    )
    service_name = models.CharField('Услуга', max_length=200)
    date = models.DateField('Дата')
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tourist} → {self.guide.name}: {self.service_name}'
