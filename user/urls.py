from django.contrib.auth.views import LogoutView
from django.urls import path

from user import views

app_name = "user"
urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
