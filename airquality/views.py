from django.shortcuts import render
from rest_framework import viewsets
from .models import AirStation, AirQualityReading
from .serializers import AirStationSerializer, AirQualityReadingSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
import logging
logger = logging.getLogger(__name__)

# Create your views here.

class AirStationViewSet(viewsets.ModelViewSet):
    queryset = AirStation.objects.all()
    serializer_class = AirStationSerializer

class AirQualityReadingViewSet(viewsets.ModelViewSet):
    queryset = AirQualityReading.objects.all()
    serializer_class = AirQualityReadingSerializer

SENSOR_LABELS = {
    4898: {'station': 'esp8266-14114907', 'type': 'PMS'},
    4899: {'station': 'esp8266-14114907', 'type': 'DHT'},
    4900: {'station': 'esp8266-14160853', 'type': 'PMS'},
    4901: {'station': 'esp8266-14160853', 'type': 'DHT'},
    4896: {'station': 'esp8266-14169100', 'type': 'PMS/DHT'},
}

PM_MAPPING = {
    'P0': 'pm1',
    'P1': 'pm10',
    'P2': 'pm25',
}

# Map known location names to user-friendly station names
STATION_NAME_MAP = {
    "Strathmore University - Auditorium parking": "Auditorium Parking",
    "Strathmore university - Gate E": "Langata Gate",
    "Strathmore University - Ole Sangale": "Central Building",
}

# Use a tighter error margin for Strathmore University
STRATHMORE_CENTER = {'lat': -1.3090, 'lng': 36.8120}
STRATHMORE_LAT_ERROR = 0.01
STRATHMORE_LNG_ERROR = 0.02

def is_within_strathmore(location):
    # Temporarily relax filter for debugging
    return True

def extract_location(item):
    # Try several possible locations for the location field
    if "location" in item:
        loc = item["location"]
        if isinstance(loc, dict):
            # Try 'name', 'label', 'description'
            for key in ["name", "label", "description"]:
                if key in loc and loc[key]:
                    return loc[key]
            # If coordinates, return as string
            if "coordinates" in loc:
                return str(loc["coordinates"])
        elif isinstance(loc, str) and loc:
            return loc
    # Try meta fields
    if "meta" in item and "location" in item["meta"]:
        return item["meta"]["location"]
    # Try top-level fields
    for key in ["location_name", "station_name", "site_name"]:
        if key in item and item[key]:
            return item[key]
    # Fallback: empty string
    return ""

class SensorNowProxy(APIView):
    def get(self, request):
        sensor_ids = [4898, 4899, 4900, 4901, 4896]
        results = []
        headers = {
            'Authorization': 'Token c185cd8e877ea9746483a55be6be17b51a6154bd'
        }
        for sid in sensor_ids:
            url = f'https://api.sensors.africa/v2/now/?sensor_id={sid}'
            resp = requests.get(url, headers=headers)
            logger.info(f"Fetched for {sid}: {resp.status_code} {resp.text[:500]}")
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else [data]
                logger.info(f"Items for {sid}: {len(items)}")
                for item in items:
                    logger.info(f"Raw item for {sid}: {item}")  # Log the raw item
                    # Use the new extract_location function
                    location_name = extract_location(item)
                    location = item.get('location')
                    if location and is_within_strathmore(location):
                        mapped_values = {}
                        for v in item.get('sensordatavalues', []):
                            key = PM_MAPPING.get(v['value_type'], v['value_type'])
                            mapped_values[key] = v['value']
                        # Use the extracted location name for user-friendly mapping
                        loc_name = location.get('name', '').strip() if isinstance(location, dict) else location_name
                        user_friendly_name = STATION_NAME_MAP.get(loc_name, loc_name)
                        # Save or get AirStation
                        station_obj, _ = AirStation.objects.get_or_create(
                            name=user_friendly_name,
                            defaults={'location': f"{location.get('latitude')},{location.get('longitude')}" if isinstance(location, dict) else ''}
                        )
                        # Save AirQualityReading
                        AirQualityReading.objects.create(
                            station=station_obj,
                            timestamp=item.get('timestamp'),
                            aqi=None,  # Not available from API
                            pm1=mapped_values.get('pm1') or 0,
                            pm25=mapped_values.get('pm25') or 0,
                            pm10=mapped_values.get('pm10') or 0,
                            temperature=mapped_values.get('temperature') or 0,
                            humidity=mapped_values.get('humidity') or 0,
                        )
                        results.append({
                            'location': user_friendly_name,
                            'timestamp': item.get('timestamp'),
                            'pm25': mapped_values.get('pm25'),
                            'pm1': mapped_values.get('pm1'),
                            'pm10': mapped_values.get('pm10'),
                            'temperature': mapped_values.get('temperature'),
                            'humidity': mapped_values.get('humidity'),
                        })
                    else:
                        # If location is missing or not within bounds, still append with extracted name
                        results.append({
                            'location': location_name,
                            'timestamp': item.get('timestamp'),
                            'pm25': item.get('pm25'),
                            'pm1': item.get('pm1'),
                            'pm10': item.get('pm10'),
                            'temperature': item.get('temperature'),
                            'humidity': item.get('humidity'),
                        })
            else:
                results.append({
                    'sensor_id': sid,
                    'station': SENSOR_LABELS[sid]['station'],
                    'type': SENSOR_LABELS[sid]['type'],
                    'error': f'HTTP {resp.status_code}',
                    'details': resp.text
                })
        return Response(results)
