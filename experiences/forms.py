from django import forms
from .models import Experience, ExperienceReview


class ExperienceForm(forms.ModelForm):
    """Форма создания / редактирования экскурсии."""

    class Meta:
        model = Experience
        fields = [
            'title', 'description', 'city', 'category',
            'duration_hours', 'price', 'mode', 'datetime',
            'meeting_point', 'max_participants', 'is_active',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'mode': forms.Select(attrs={'class': 'form-select'}),
            'datetime': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'meeting_point': forms.TextInput(attrs={'class': 'form-control'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['datetime'].widget = forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            )
            if self.instance.datetime:
                self.initial['datetime'] = self.instance.datetime.strftime('%Y-%m-%dT%H:%M')


class ExperienceReviewForm(forms.ModelForm):
    """Форма отзыва."""

    class Meta:
        model = ExperienceReview
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(
                choices=[(5, '5 — Отлично'), (4, '4 — Хорошо'), (3, '3 — Нормально'),
                         (2, '2 — Плохо'), (1, '1 — Ужасно')],
                attrs={'class': 'form-select'},
            ),
            'text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Расскажите о своих впечатлениях...',
            }),
        }
