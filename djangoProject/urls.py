from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path

from tasks import views
from tasks.services import tasks_actions, objects

urlpatterns = [
    path("create-task/", tasks_actions.create_task, name="create_task"),
    path("create-object/", objects.create_object, name="create_object"),
    path("take_task/<int:task_id>/", tasks_actions.take_task, name="take_task"),
    path("delete_task/<int:task_id>/", tasks_actions.delete_task, name="delete_task"),
    path("edit-task/<int:task_id>/", tasks_actions.edit_task, name="edit_task"),
    path("edit-obj/<slug:object_slug>/", objects.edit_object, name="edit_object"),
    path("close_task/<int:task_id>/", tasks_actions.close_task, name="close_task"),
    path("reopen_task/<int:task_id>/", tasks_actions.reopen_task, name="reopen_task"),
    path("export_to_excel/", tasks_actions.export_to_excel, name="export-xls"),
    path("tasks/", views.get_tasks_page, name="tasks"),  # Страница задач
    path("calendar/", views.get_calendar_page, name="calendar"),  # Страница карты
    path("stat/", views.get_stat_page, name="stat"),  # Страница карты
    path("object/<slug:object_slug>/", views.get_object_page, name="show-object"),
    path("", views.get_home, name="home"),
    path("admin/",admin.site.urls),
    path("user/", include("user.urls", namespace="user")),
    path("ajax/tasks/<int:task_id>/", views.get_task_view, name="ajax-show-task"),
    path("ajax/tasks/<int:task_id>/edit", views.get_task_edit_form, name="ajax-task-edit-form"),
    path("ajax/objects/<slug:slug>/edit", views.get_obj_edit_form, name="ajax-obj-edit-form"),
    path('ajax/tasks/<int:task_id>/action/<str:action_type>', views.get_task_action_form, name='ajax-task-action-form'),

    # CKEDITOR
    path('ckeditor/', include('ckeditor_uploader.urls')),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += debug_toolbar_urls()
