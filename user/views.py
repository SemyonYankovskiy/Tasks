from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from user.forms import LoginForm


class CustomLoginView(LoginView):
    authentication_form = LoginForm
    template_name = 'login.html'
    #extra_context = {'title': 'Авторизация на сайте'}

    def get_success_url(self):
        return reverse_lazy('home')