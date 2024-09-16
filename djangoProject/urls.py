from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path

from tasks import views

urlpatterns = [
    path('create-task/', views.create_task, name='create_task'),
    path('edit-task/<int:task_id>/', views.edit_task, name='edit_task'),
    path("tasks/", views.tasks_page, name="tasks"),  # Страница задач
    path("close_task/<int:task_id>/", views.close_task, name="close_task"),
    path("reopen_task/<int:task_id>/", views.reopen_task, name="reopen_task"),
    path("map/", views.map_page, name="map"),  # Страница карты
    path("calendar/", views.calendar, name="calendar"),  # Страница карты
    path("admin/", admin.site.urls, ),
    path("user/", include("user.urls", namespace="user")),
    path("object/<slug:object_slug>/", views.get_object_page, name="show-object"),
    path("", views.get_home, name="home"),
    path("ajax/tasks/<int:task_id>/", views.get_task_view, name="ajax-show-task"),
    path("ajax/tasks/<int:task_id>/edit", views.get_task_edit_form, name="ajax-task-edit-form")
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += debug_toolbar_urls()
