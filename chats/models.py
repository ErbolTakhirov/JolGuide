from django.db import models
from django.conf import settings


class ChatMessage(models.Model):
    """Сообщение в чате между двумя пользователями."""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name='Получатель',
    )
    text = models.TextField('Сообщение')
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)
    is_read = models.BooleanField('Прочитано', default=False)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} → {self.receiver}: {self.text[:40]}'
