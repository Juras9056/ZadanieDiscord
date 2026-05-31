from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls', namespace='core')),
    path('users/', include('apps.users.urls', namespace='users')),
    path('chat/', include('apps.chat.urls', namespace='chat')),
    path('moderation/', include('apps.moderation.urls', namespace='moderation')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'
