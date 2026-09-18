from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

# Configurar títulos do admin
#admin.site.site_header = "Otsulde Minas"
#admin.site.site_title = "Otsulde Minas - Admin"
admin.site.index_title = ""

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include('api.urls')),
    path('backend/', include('website_backend.urls')),
    path('schema/', include('schema_viewer.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

