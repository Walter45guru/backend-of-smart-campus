from django.core.management.base import BaseCommand
from airquality.models import AirStation, AirQualityReading
import requests
from collections import defaultdict
import datetime

SENSOR_METADATA = {
    4898: {"station": "Auditorium Parking", "lat": -1.309, "lon": 36.812, "type": "PMS"},
    4899: {"station": "Auditorium Parking", "lat": -1.309, "lon": 36.812, "type": "DHT"},
    4900: {"station": "Langata Gate", "lat": -1.310, "lon": 36.813, "type": "PMS"},
    4901: {"station": "Langata Gate", "lat": -1.310, "lon": 36.813, "type": "DHT"},
    4896: {"station": "Central Building", "lat": -1.311, "lon": 36.814, "type": "PMS/DHT"},
}

PM_MAPPING = {
    'P0': 'pm1',
    'P1': 'pm10',
    'P2': 'pm25',
}

class Command(BaseCommand):
    help = 'Fetch and save new data from external Sensors.Africa API for each sensor.'

    def handle(self, *args, **options):
        sensor_ids = list(SENSOR_METADATA.keys())
        headers = {
            'Authorization': 'Token c185cd8e877ea9746483a55be6be17b51a6154bd'
        }
        for sid in sensor_ids:
            meta = SENSOR_METADATA[sid]
            # Find latest timestamp for this station
            station_obj, _ = AirStation.objects.get_or_create(
                name=meta['station'],
                defaults={'location': f"{meta['lat']},{meta['lon']}"}
            )
            latest = AirQualityReading.objects.filter(station=station_obj).order_by('-timestamp').first()
            start_time = None
            if latest:
                # Add 1 second to avoid duplicate
                start_time = (latest.timestamp + datetime.timedelta(seconds=1)).isoformat()
            # Build API URL
            url = f'https://api.sensors.africa/v2/measurements/?sensor_id={sid}'
            if start_time:
                url += f'&timestamp__gte={start_time}'
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else [data]
                for item in items:
                    mapped_values = {}
                    for v in item.get('sensordatavalues', []):
                        key = PM_MAPPING.get(v['value_type'], v['value_type'])
                        mapped_values[key] = v['value']
                    ts = item.get('timestamp')
                    # Save reading (if not already exists for this station and timestamp)
                    if not AirQualityReading.objects.filter(station=station_obj, timestamp=ts).exists():
                        AirQualityReading.objects.create(
                            station=station_obj,
                            timestamp=ts,
                            aqi=None,
                            pm1=mapped_values.get('pm1') or 0,
                            pm25=mapped_values.get('pm25') or 0,
                            pm10=mapped_values.get('pm10') or 0,
                            temperature=mapped_values.get('temperature') or 0,
                            humidity=mapped_values.get('humidity') or 0,
                        )
        self.stdout.write(self.style.SUCCESS('External data incrementally ingested and saved.')) 