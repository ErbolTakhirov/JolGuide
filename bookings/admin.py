from django.contrib import admin
from .models import BookingRequest


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ('tourist', 'guide', 'service_name', 'date', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('service_name', 'tourist__email', 'guide__name')
