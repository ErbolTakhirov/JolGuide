from django.contrib import admin
from .models import MatchRequest, MatchResult


class MatchResultInline(admin.TabularInline):
    model = MatchResult
    extra = 0
    readonly_fields = ('guide', 'score', 'reason', 'compromise')


@admin.register(MatchRequest)
class MatchRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'tourist', 'prompt_short', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('prompt',)
    inlines = [MatchResultInline]

    @admin.display(description='Запрос')
    def prompt_short(self, obj):
        return obj.prompt[:80]


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('match_request', 'guide', 'score', 'reason_short')
    list_filter = ('score',)

    @admin.display(description='Причина')
    def reason_short(self, obj):
        return obj.reason[:80]
