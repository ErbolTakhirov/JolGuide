"""Guides app: модели верификации гидов и жалоб."""
from django.db import models
from django.conf import settings
from accounts.models import GuideProfile


class GuideVerificationRequest(models.Model):
    """Заявка на верификацию гида."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        SUBMITTED = 'submitted', 'Отправлена'
        UNDER_REVIEW = 'under_review', 'На рассмотрении'
        APPROVED_LIMITED = 'approved_limited', 'Одобрена'
        REJECTED = 'rejected', 'Отклонена'
        SUSPENDED = 'suspended', 'Приостановлена'

    class RiskLevel(models.TextChoices):
        LOW = 'low', 'Низкий'
        MEDIUM = 'medium', 'Средний'
        HIGH = 'high', 'Высокий'

    guide = models.OneToOneField(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='verification_request',
        verbose_name='Гид',
    )

    # --- Identity fields ---
    legal_name = models.CharField('Полное имя (по документу)', max_length=200)
    display_name = models.CharField('Отображаемое имя', max_length=150)
    phone = models.CharField('Телефон', max_length=30)
    city = models.CharField('Город', max_length=100)
    languages = models.CharField(
        'Языки', max_length=200,
        help_text='Через запятую, напр: ru, en, de',
    )
    bio = models.TextField('О себе', blank=True)
    service_types = models.TextField(
        'Типы услуг', blank=True,
        help_text='Какие экскурсии / услуги предлагаете',
    )
    risk_level = models.CharField(
        'Уровень риска',
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
    )

    # --- Documents ---
    id_document_image = models.ImageField(
        'Документ (фото)',
        upload_to='verification/ids/',
    )
    selfie_image = models.ImageField(
        'Селфи',
        upload_to='verification/selfies/',
    )

    # --- Agreement ---
    agreed_to_safety_rules = models.BooleanField(
        'Согласен с правилами безопасности', default=False,
    )

    # --- Status workflow ---
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    internal_notes = models.TextField('Внутренние заметки (для админа)', blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_verifications',
        verbose_name='Проверил',
    )
    reviewed_at = models.DateTimeField('Дата проверки', null=True, blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Заявка на верификацию'
        verbose_name_plural = 'Заявки на верификацию'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.guide.name} — {self.get_status_display()}'

    def save(self, *args, **kwargs):
        """Sync GuideProfile.is_verified based on status."""
        super().save(*args, **kwargs)
        if self.status == self.Status.APPROVED_LIMITED:
            GuideProfile.objects.filter(pk=self.guide_id).update(is_verified=True)
        elif self.status in (self.Status.REJECTED, self.Status.SUSPENDED):
            GuideProfile.objects.filter(pk=self.guide_id).update(is_verified=False)


class GuideReport(models.Model):
    """Жалоба на гида."""
    guide = models.ForeignKey(
        GuideProfile,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='Гид',
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='guide_reports',
        verbose_name='Пожаловался',
    )
    reason = models.TextField('Причина')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Жалоба на гида'
        verbose_name_plural = 'Жалобы на гидов'
        ordering = ['-created_at']

    def __str__(self):
        reporter = self.reported_by.email if self.reported_by else 'Аноним'
        return f'{reporter} → {self.guide.name}'
