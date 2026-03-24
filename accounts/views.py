from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
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
            # Создаём профиль в зависимости от роли
            if user.role == User.Role.TOURIST:
                TouristProfile.objects.create(user=user, name=user.username)
            elif user.role == User.Role.GUIDE:
                GuideProfile.objects.create(user=user, name=user.username, city='')
            login(request, user)
            return redirect('home')
        return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    """Вход по email."""
    form_class = LoginForm
    template_name = 'accounts/login.html'


def logout_view(request):
    """Выход из аккаунта."""
    logout(request)
    return redirect('home')
