from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError


def validate_image_size(image):
    """Ограничение размера файла (напр. 2МБ)."""
    file_size = image.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Максимальный размер файла — {limit_mb}МБ")


class User(AbstractUser):
    """Расширенный пользователь с ролями."""

    class Role(models.TextChoices):
        TOURIST = 'tourist', 'Турист'
        GUIDE = 'guide', 'Гид'
        ADMIN = 'admin', 'Админ'

    email = models.EmailField('Email', unique=True)
    role = models.CharField(
        'Роль',
        max_length=10,
        choices=Role.choices,
        default=Role.TOURIST,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.email} ({self.get_role_display()})'


class TouristProfile(models.Model):
    """Профиль туриста."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tourist_profile',
        verbose_name='Пользователь',
    )
    name = models.CharField('Имя', max_length=150, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True)
    city = models.CharField('Город', max_length=100, blank=True)
    languages = models.CharField('Языки', max_length=200, blank=True,
                                 help_text='Через запятую, напр: ru, en')
    preferences_text = models.TextField('Предпочтения', blank=True)

    class Meta:
        verbose_name = 'Профиль туриста'
        verbose_name_plural = 'Профили туристов'

    def __str__(self):
        return self.name or self.user.email


class GuideProfile(models.Model):
    """Профиль гида."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='guide_profile',
        verbose_name='Пользователь',
    )
    name = models.CharField('Имя', max_length=150, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True,
                               validators=[validate_image_size])
    photo = models.ImageField('Фото (портфолио)', upload_to='guides/photos/', blank=True,
                              validators=[validate_image_size])
    city = models.CharField('Город', max_length=100, blank=True)
    languages = models.CharField('Языки', max_length=200, blank=True,
                                 help_text='Через запятую, напр: ru, en, de')
    bio = models.TextField('О себе', blank=True)
    services_text = models.TextField('Услуги', blank=True)
    price_from = models.DecimalField('Цена от', max_digits=10, decimal_places=2,
                                     default=0)
    rating = models.FloatField('Рейтинг', default=0)
    is_verified = models.BooleanField('Верифицирован', default=False)

    class Meta:
        verbose_name = 'Профиль гида'
        verbose_name_plural = 'Профили гидов'

    def __str__(self):
        return f'{self.name or self.user.email} — {self.city}'

    def update_rating(self):
        """Пересчитывает средний рейтинг на основе отзывов."""
        avg_rating = self.reviews.aggregate(Avg('rating'))['rating__avg']
        self.rating = round(avg_rating, 2) if avg_rating else 0
        self.save()


