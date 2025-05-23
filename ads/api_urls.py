from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ads.api_views import AdViewSet, ExchangeProposalViewSet

router = DefaultRouter()
router.register(r'ads', AdViewSet)
router.register(r'proposals', ExchangeProposalViewSet)

urlpatterns = [
    path('', include(router.urls)),
]