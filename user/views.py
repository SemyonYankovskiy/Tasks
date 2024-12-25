from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy

from user.forms import LoginForm


class CustomLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Перенаправляем авторизованных пользователей
            return redirect(reverse_lazy("home"))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("home")
