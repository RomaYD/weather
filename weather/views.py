from django.shortcuts import render
from django.http import JsonResponse
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import requests
from django.conf import settings
from .models import SearchHistory


def city_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)
    username = getattr(settings, 'GEONAMES_USERNAME', 'demo')
    url = f'http://api.geonames.org/searchJSON?q={query}&maxRows=5&username={username}'
    response = requests.get(url, timeout=3)
    response.raise_for_status()
    data = response.json()
    results = [
        {
            'name': place['name'],
            'country': place.get('countryName', '')
        }
        for place in data.get('geonames', [])
        if 'name' in place
    ]
    return JsonResponse(results, safe=False)


def index(request):
    return render(request, 'weather/index.html')


def get_weather(request):
    if request.method == 'POST':
        city = request.POST.get('city', '').strip()
        if not city:
            return JsonResponse({'error': 'Введите название города'}, status=400)
        if not request.session.session_key:
            request.session.create()
        obj, created = SearchHistory.objects.get_or_create(
            session_id=request.session.session_key,
            city=city,
            defaults={'search_count': 1}
        )
        if not created:
            obj.search_count += 1
            obj.save()
        lon, lat = get_coordinates(city)
        if not lon or not lat:
            return JsonResponse({'error': 'Город не найден'}, status=404)
        weather_data = fetch_weather(lat, lon)
        return JsonResponse(weather_data)
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)


def get_coordinates(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?city={city_name}&format=json"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]['lon']), float(data[0]['lat'])
        return None, None
    except Exception:
        return None, None


def fetch_weather(latitude, longitude):
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["temperature_2m", "rain", "snowfall", "cloud_cover"],
        "timezone": "auto",
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ).strftime('%Y-%m-%d %H:%M').tolist(),
        "temperature": hourly.Variables(0).ValuesAsNumpy().tolist(),
        "rain": hourly.Variables(1).ValuesAsNumpy().tolist(),
        "snowfall": hourly.Variables(2).ValuesAsNumpy().tolist(),
        "cloud_cover": hourly.Variables(3).ValuesAsNumpy().tolist()
    }
    return hourly_data
