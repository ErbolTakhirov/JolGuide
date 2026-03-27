from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, GuideProfile, TouristProfile
from matching.services import invalidate_guide_cache

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == User.Role.GUIDE:
            GuideProfile.objects.create(user=instance)
        else:
            TouristProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == User.Role.GUIDE:
        if hasattr(instance, 'guide_profile'):
            instance.guide_profile.save()
    else:
        if hasattr(instance, 'tourist_profile'):
            instance.tourist_profile.save()

@receiver(post_save, sender=GuideProfile)
def invalidate_cache_on_guide_update(sender, instance, **kwargs):
    """Сброс кеша CAG при обновлении профиля гида."""
    if instance.city:
        invalidate_guide_cache(instance.city)
