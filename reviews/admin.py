from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('tourist', 'guide', 'rating', 'text_short', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('text', 'tourist__email', 'guide__name')

    @admin.display(description='Текст')
    def text_short(self, obj):
        return obj.text[:60]
