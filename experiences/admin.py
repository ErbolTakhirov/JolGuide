from django.contrib import admin
from .models import Experience, ExperienceBooking, ExperienceReview, GuideFeedbackSummary


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'guide', 'mode', 'city', 'price', 'datetime', 'seats_left', 'is_active')
    list_filter = ('mode', 'category', 'is_active', 'city')
    search_fields = ('title', 'guide__name')


@admin.register(ExperienceBooking)
class ExperienceBookingAdmin(admin.ModelAdmin):
    list_display = ('experience', 'tourist', 'num_guests', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(ExperienceReview)
class ExperienceReviewAdmin(admin.ModelAdmin):
    list_display = ('experience', 'tourist', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(GuideFeedbackSummary)
class GuideFeedbackSummaryAdmin(admin.ModelAdmin):
    list_display = ('guide', 'source_review_count', 'generated_at')
    readonly_fields = ('summary_text', 'source_review_count', 'generated_at')
