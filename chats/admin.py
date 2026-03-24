from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'text_short', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'sender__email', 'receiver__email')

    @admin.display(description='Текст')
    def text_short(self, obj):
        return obj.text[:60]
