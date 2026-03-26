"""Experiences app: модели экскурсий, бронирований, отзывов и AI-фидбека."""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import GuideProfile


class Experience(models.Model):
    """Экскурсия / услуга гида."""

    class Mode(models.TextChoices):
        PRIVATE = 'private', 'Приватная'
        GROUP = 'group', 'Групповая'

    class Category(models.TextChoices):
        WALKING = 'walking', 'Пешая'
        DRIVING = 'driving', 'На транспорте'
        FOOD = 'food', 'Гастро-тур'
        ADVENTURE = 'adventure', 'Приключение'
        CULTURE = 'culture', 'Культура'
        NATURE = 'nature', 'Природа'
        OTHER = 'other', 'Другое'

    guide = models.ForeignKey(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='experiences',
        verbose_name='Гид',
    )
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание')
    city = models.CharField('Город / район', max_length=100)
    category = models.CharField(
        'Категория', max_length=20,
        choices=Category.choices, default=Category.OTHER,
    )
    duration_hours = models.DecimalField(
        'Длительность (часов)', max_digits=4, decimal_places=1, default=2,
    )
    price = models.DecimalField('Цена ($)', max_digits=10, decimal_places=2)
    mode = models.CharField(
        'Режим', max_length=10,
        choices=Mode.choices, default=Mode.PRIVATE,
    )
    datetime = models.DateTimeField('Дата и время')
    meeting_point = models.CharField('Место встречи', max_length=300, blank=True)
    max_participants = models.PositiveIntegerField(
        'Макс. участников', default=1,
        help_text='Для приватных = 1, для групповых > 1',
    )
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Экскурсия'
        verbose_name_plural = 'Экскурсии'
        ordering = ['datetime']

    def __str__(self):
        return f'{self.title} ({self.get_mode_display()}) — {self.guide.name}'

    @property
    def confirmed_count(self):
        """Кол-во подтверждённых бронирований."""
        return self.bookings.filter(
            status__in=(ExperienceBooking.Status.PENDING, ExperienceBooking.Status.CONFIRMED)
        ).aggregate(total=models.Sum('num_guests'))['total'] or 0

    @property
    def seats_left(self):
        return max(0, self.max_participants - self.confirmed_count)

    @property
    def is_fully_booked(self):
        return self.seats_left <= 0

    @property
    def avg_rating(self):
        result = self.reviews.aggregate(avg=models.Avg('rating'))
        return round(result['avg'] or 0, 1)

    @property
    def review_count(self):
        return self.reviews.count()


class ExperienceBooking(models.Model):
    """Бронирование экскурсии."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'В ожидании'
        CONFIRMED = 'confirmed', 'Подтверждено'
        COMPLETED = 'completed', 'Завершено'
        CANCELLED = 'cancelled', 'Отменено'

    experience = models.ForeignKey(
        Experience,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Экскурсия',
    )
    tourist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='experience_bookings',
        verbose_name='Турист',
    )
    num_guests = models.PositiveIntegerField('Кол-во гостей', default=1)
    status = models.CharField(
        'Статус', max_length=12,
        choices=Status.choices, default=Status.PENDING,
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Бронирование экскурсии'
        verbose_name_plural = 'Бронирования экскурсий'
        ordering = ['-created_at']
        unique_together = [('experience', 'tourist')]

    def __str__(self):
        return f'{self.tourist.username} → {self.experience.title}'


class ExperienceReview(models.Model):
    """Отзыв к конкретной экскурсии (после завершения)."""
    booking = models.OneToOneField(
        ExperienceBooking,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='Бронирование',
    )
    experience = models.ForeignKey(
        Experience,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Экскурсия',
    )
    guide = models.ForeignKey(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='experience_reviews',
        verbose_name='Гид',
    )
    tourist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='experience_reviews',
        verbose_name='Турист',
    )
    rating = models.PositiveSmallIntegerField(
        'Оценка',
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField('Текст отзыва', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв на экскурсию'
        verbose_name_plural = 'Отзывы на экскурсии'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tourist.username} → {self.experience.title}: {self.rating}★'


class GuideFeedbackSummary(models.Model):
    """AI-сгенерированная сводка по отзывам для гида."""
    guide = models.OneToOneField(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='feedback_summary',
        verbose_name='Гид',
    )
    summary_text = models.TextField('Сводка')
    source_review_count = models.PositiveIntegerField('Кол-во отзывов', default=0)
    generated_at = models.DateTimeField('Сгенерировано', auto_now=True)

    class Meta:
        verbose_name = 'AI-сводка отзывов'
        verbose_name_plural = 'AI-сводки отзывов'

    def __str__(self):
        return f'Сводка для {self.guide.name} ({self.source_review_count} отзывов)'
