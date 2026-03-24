from django.contrib.auth.models import AbstractUser
from django.db import models


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
    name = models.CharField('Имя', max_length=150)
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
    name = models.CharField('Имя', max_length=150)
    photo = models.ImageField('Фото', upload_to='guides/photos/', blank=True)
    city = models.CharField('Город', max_length=100)
    languages = models.CharField('Языки', max_length=200,
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
        return f'{self.name} — {self.city}'
