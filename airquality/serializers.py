from rest_framework import serializers
from .models import AirStation, AirQualityReading

class AirQualityReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirQualityReading
        fields = '__all__'

class AirStationSerializer(serializers.ModelSerializer):
    readings = AirQualityReadingSerializer(many=True, read_only=True)
    class Meta:
        model = AirStation
        fields = ['id', 'name', 'location', 'readings'] 