
from django.urls import path, re_path
from tasks import views

urlpatterns = [
    path('object/1', views.get_object_page),
    path('', views.index),
]
