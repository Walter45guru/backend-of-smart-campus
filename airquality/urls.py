from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AirStationViewSet, AirQualityReadingViewSet, SensorNowProxy, AirQualityReadingExportView, StationReadingsByIdView, StationReadingsByNameView

router = DefaultRouter()
router.register(r'stations', AirStationViewSet)
router.register(r'readings', AirQualityReadingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('proxy/now/', SensorNowProxy.as_view()),
    path('readings/export/', AirQualityReadingExportView.as_view()),
    path('stations/<int:station_id>/readings/', StationReadingsByIdView.as_view()),
    path('stations/name/<str:station_name>/readings/', StationReadingsByNameView.as_view()),
] 