from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.schemas import get_schema_view
from rest_framework import permissions


schema_view = get_schema_view(
    title="Barter Platform API",
    description="API для управления объявлениями и предложениями об обмене",
    version="1.0.0",
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('ads.api_urls')),
    path('', include('ads.urls')),
    path('', RedirectView.as_view(url='/ads/', permanent=False)),
    path('api/schema/', schema_view, name='api-schema'),
    path('api/docs/', schema_view, name='api-docs'),

]