"""Формы для верификации гидов и жалоб."""
from django import forms
from .models import GuideVerificationRequest, GuideReport


class VerificationRequestForm(forms.ModelForm):
    """Форма подачи заявки на верификацию."""

    agreed_to_safety_rules = forms.BooleanField(
        label='Я согласен(на) с правилами безопасности платформы',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = GuideVerificationRequest
        fields = [
            'legal_name', 'display_name', 'phone', 'city',
            'languages', 'bio', 'service_types', 'risk_level',
            'id_document_image', 'selfie_image',
            'agreed_to_safety_rules',
        ]
        widgets = {
            'legal_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иванов Иван Иванович',
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иван',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+996 555 123456',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Бишкек',
            }),
            'languages': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ru, en, de',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Расскажите о себе...',
            }),
            'service_types': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Пешие экскурсии, авто-туры, горный треккинг...',
            }),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'id_document_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'selfie_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }


class GuideReportForm(forms.ModelForm):
    """Форма жалобы на гида."""

    class Meta:
        model = GuideReport
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите причину жалобы...',
                'required': True,
            }),
        }
        labels = {
            'reason': 'Причина жалобы',
        }
