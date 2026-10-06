from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

admin.site.index_title = ""

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include('api.urls')),
    path('backend/', include('website_backend.urls')),
  	path('ckeditor5/', include('django_ckeditor_5.urls')),
		
		# SWAGGER
    path('schema/', SpectacularAPIView.as_view(), name='backend-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='backend-schema'), name='backend-swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

