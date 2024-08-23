from django.urls import path
from tasks import views
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from debug_toolbar.toolbar import debug_toolbar_urls
from django.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('user.urls', namespace='user')),
    path('object/<slug:object_slug>/', views.get_object_page, name='show-object'),
    path('', views.get_home, name='home'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += debug_toolbar_urls()
