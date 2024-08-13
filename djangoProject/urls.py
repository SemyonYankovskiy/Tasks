
from django.urls import path
from tasks import views
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from debug_toolbar.toolbar import debug_toolbar_urls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('object/<int:object_id>/', views.get_object_page, name='show-object'),
    path('', views.get_home, name='home'),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += debug_toolbar_urls()