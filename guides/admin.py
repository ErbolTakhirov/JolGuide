"""Admin для верификации гидов и жалоб."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import GuideVerificationRequest, GuideReport


@admin.register(GuideVerificationRequest)
class GuideVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('guide', 'legal_name', 'status', 'risk_level', 'reviewed_by', 'created_at')
    list_filter = ('status', 'risk_level', 'created_at')
    search_fields = ('legal_name', 'display_name', 'guide__name', 'city')
    readonly_fields = (
        'guide', 'created_at', 'updated_at',
        'id_document_preview', 'selfie_preview',
    )
    fieldsets = (
        ('Гид', {
            'fields': ('guide',),
        }),
        ('Личные данные', {
            'fields': (
                'legal_name', 'display_name', 'phone', 'city',
                'languages', 'bio', 'service_types', 'risk_level',
            ),
        }),
        ('Документы', {
            'fields': (
                'id_document_image', 'id_document_preview',
                'selfie_image', 'selfie_preview',
            ),
        }),
        ('Соглашение', {
            'fields': ('agreed_to_safety_rules',),
        }),
        ('Проверка (admin)', {
            'fields': ('status', 'internal_notes', 'reviewed_by', 'reviewed_at'),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    actions = ['approve_selected', 'reject_selected']

    def id_document_preview(self, obj):
        if obj.id_document_image:
            return format_html(
                '<img src="{}" style="max-height:300px; max-width:400px;" />',
                obj.id_document_image.url,
            )
        return '—'
    id_document_preview.short_description = 'Превью документа'

    def selfie_preview(self, obj):
        if obj.selfie_image:
            return format_html(
                '<img src="{}" style="max-height:300px; max-width:400px;" />',
                obj.selfie_image.url,
            )
        return '—'
    selfie_preview.short_description = 'Превью селфи'

    def save_model(self, request, obj, form, change):
        """Auto-fill reviewed_by and reviewed_at when admin changes status."""
        if change and 'status' in form.changed_data:
            if obj.status in (
                GuideVerificationRequest.Status.APPROVED_LIMITED,
                GuideVerificationRequest.Status.REJECTED,
                GuideVerificationRequest.Status.SUSPENDED,
            ):
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description='✅ Одобрить выбранные заявки')
    def approve_selected(self, request, queryset):
        for obj in queryset:
            obj.status = GuideVerificationRequest.Status.APPROVED_LIMITED
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()
        self.message_user(request, f'Одобрено заявок: {queryset.count()}')

    @admin.action(description='❌ Отклонить выбранные заявки')
    def reject_selected(self, request, queryset):
        for obj in queryset:
            obj.status = GuideVerificationRequest.Status.REJECTED
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()
        self.message_user(request, f'Отклонено заявок: {queryset.count()}')


@admin.register(GuideReport)
class GuideReportAdmin(admin.ModelAdmin):
    list_display = ('guide', 'reported_by', 'reason_short', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('guide__name', 'reason', 'reported_by__email')
    readonly_fields = ('guide', 'reported_by', 'reason', 'created_at')

    def reason_short(self, obj):
        return obj.reason[:80] + '...' if len(obj.reason) > 80 else obj.reason
    reason_short.short_description = 'Причина'
