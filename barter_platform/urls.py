from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.schemas import get_schema_view
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="Barter Platform API",
        default_version='v1',
        description="API для платформы обмена вещами",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('ads.api_urls')),
    path('', include('ads.urls')),
    path('', RedirectView.as_view(url='/ads/', permanent=False)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]