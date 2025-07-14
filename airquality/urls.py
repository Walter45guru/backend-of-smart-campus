from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AirStationViewSet, AirQualityReadingViewSet, SensorNowProxy

router = DefaultRouter()
router.register(r'stations', AirStationViewSet)
router.register(r'readings', AirQualityReadingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('proxy/now/', SensorNowProxy.as_view()),
] 