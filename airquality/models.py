from django.db import models

# Create your models here.

class AirStation(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    # Add more fields if needed

class AirQualityReading(models.Model):
    station = models.ForeignKey(AirStation, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.DateTimeField(auto_now_add=True)
    aqi = models.FloatField()
    pm1 = models.FloatField()
    pm25 = models.FloatField()
    pm10 = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
