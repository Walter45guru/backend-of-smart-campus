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

SENSOR_LOCATIONS = {
    4898: "Auditorium Parking",
    4899: "Auditorium Parking",
    4900: "Langata Gate",
    4901: "Langata Gate",
    4896: "Central Building",
}

SENSOR_METADATA = {
    4898: {"station": "Auditorium Parking", "lat": -1.309, "lon": 36.812, "type": "PMS"},
    4899: {"station": "Auditorium Parking", "lat": -1.309, "lon": 36.812, "type": "DHT"},
    4900: {"station": "Langata Gate", "lat": -1.310, "lon": 36.813, "type": "PMS"},
    4901: {"station": "Langata Gate", "lat": -1.310, "lon": 36.813, "type": "DHT"},
    4896: {"station": "Central Building", "lat": -1.311, "lon": 36.814, "type": "PMS/DHT"},
}

class SensorNowProxy(APIView):
    def get(self, request):
        import datetime
        from collections import defaultdict
        sensor_ids = list(SENSOR_METADATA.keys())
        headers = {
            'Authorization': 'Token c185cd8e877ea9746483a55be6be17b51a6154bd'
        }
        # Collect readings by station and timestamp (rounded to nearest minute)
        station_data = defaultdict(list)
        for sid in sensor_ids:
            url = f'https://api.sensors.africa/v2/now/?sensor_id={sid}'
            resp = requests.get(url, headers=headers)
            logger.info(f"Fetched for {sid}: {resp.status_code} {resp.text[:500]}")
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else [data]
                for item in items:
                    mapped_values = {}
                    for v in item.get('sensordatavalues', []):
                        key = PM_MAPPING.get(v['value_type'], v['value_type'])
                        mapped_values[key] = v['value']
                    meta = SENSOR_METADATA.get(sid)
                    if not meta:
                        continue
                    # Parse timestamp and round to nearest minute for grouping
                    ts = item.get('timestamp')
                    try:
                        dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        rounded_dt = dt.replace(second=0, microsecond=0)
                    except Exception:
                        rounded_dt = ts
                    station_key = (meta['station'], rounded_dt)
                    station_data[station_key].append({
                        'sensor_id': sid,
                        'type': meta['type'],
                        'lat': meta['lat'],
                        'lon': meta['lon'],
                        'timestamp': ts,
                        **mapped_values
                    })
        # Merge PMS and DHT readings for each station/timestamp
        results = []
        for (station, rounded_dt), readings in station_data.items():
            merged = {
                'station': station,
                'lat': readings[0]['lat'],
                'lon': readings[0]['lon'],
                'timestamp': readings[0]['timestamp'],
                'pm1': None,
                'pm25': None,
                'pm10': None,
                'temperature': None,
                'humidity': None
            }
            for r in readings:
                if 'pm1' in r: merged['pm1'] = r['pm1']
                if 'pm25' in r: merged['pm25'] = r['pm25']
                if 'pm10' in r: merged['pm10'] = r['pm10']
                if 'temperature' in r: merged['temperature'] = r['temperature']
                if 'humidity' in r: merged['humidity'] = r['humidity']
            results.append(merged)
        return Response(results)
