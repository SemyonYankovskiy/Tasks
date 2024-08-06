
from django.urls import path
from tasks import views
from django.contrib import admin



urlpatterns = [
    path('admin/', admin.site.urls),
    path('object/1', views.get_object_page),
    path('', views.index),
]
