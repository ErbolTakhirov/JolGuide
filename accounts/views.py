from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.views import View
from .forms import RegisterForm, LoginForm
from .models import TouristProfile, GuideProfile, User


class RegisterView(View):
    """Регистрация нового пользователя."""

    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Профили создаются автоматически сигналами в models.py
            login(request, user)
            return redirect('accounts:profile_redirect')
        return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    """Вход по email."""
    form_class = LoginForm
    template_name = 'accounts/login.html'


def logout_view(request):
    """Выход из аккаунта."""
    logout(request)
    return redirect('home')


@login_required
def profile_redirect_view(request):
    """Перенаправляет пользователя после входа/регистрации в зависимости от роли."""
    if request.user.role == User.Role.GUIDE:
        return redirect('guides:list')  # Пока на общий список, можно на личный профиль
    return redirect('home')
