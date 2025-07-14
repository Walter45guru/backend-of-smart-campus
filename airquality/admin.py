from django.contrib import admin
from .models import AirStation, AirQualityReading

@admin.register(AirStation)
class AirStationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location')
    search_fields = ('name', 'location')

@admin.register(AirQualityReading)
class AirQualityReadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_station_name', 'timestamp', 'pm25', 'pm1', 'pm10', 'temperature', 'humidity')
    list_filter = ('station', 'timestamp')
    search_fields = ('station__name',)

    def get_station_name(self, obj):
        return obj.station.name if obj.station else ''
    get_station_name.short_description = 'Location'
