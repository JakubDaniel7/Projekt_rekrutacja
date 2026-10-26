"""
Current weather for a city: Nominatim (city -> coordinates) + Open-Meteo (coordinates -> weather).

How the number of external requests is kept low:
- coordinates are cached for a week (cities do not move), weather for 30 minutes,
- "city not found" is cached too, so a typo does not hit Nominatim on every page view,
- Nominatim calls are spaced at least 1 second apart, as its usage policy requires,
- the browser asks once per unique city on the page, not once per contact.
"""
import threading
import time
from urllib.parse import quote

import requests
from django.core.cache import cache

GEOCODING_URL = "https://nominatim.openstreetmap.org/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
# Nominatim's usage policy requires an application-specific User-Agent
USER_AGENT = "contact-manager-recruitment-task/1.0"
REQUEST_TIMEOUT = 5  # seconds

COORDINATES_TTL = 60 * 60 * 24 * 7  # one week
WEATHER_TTL = 60 * 30  # 30 minutes

_MISSING = object()  # tells "not in cache" apart from a cached None ("city not found")
_nominatim_lock = threading.Lock()
_last_nominatim_call = 0.0


class WeatherUnavailable(Exception):
    """An external service did not respond or returned unexpected data."""


def get_weather(city):
    """Return the current weather for a city as a dict, or None if the city cannot be found."""
    key = "weather:" + _cache_key(city)
    weather = cache.get(key, _MISSING)
    if weather is _MISSING:
        coordinates = get_coordinates(city)
        weather = _fetch_weather(*coordinates) if coordinates else None
        cache.set(key, weather, WEATHER_TTL)
    return weather


def get_coordinates(city):
    """Return (latitude, longitude) of a city, or None if Nominatim does not know it."""
    key = "coordinates:" + _cache_key(city)
    coordinates = cache.get(key, _MISSING)
    if coordinates is _MISSING:
        coordinates = _fetch_coordinates(city)
        cache.set(key, coordinates, COORDINATES_TTL)
    return coordinates


def _fetch_coordinates(city):
    _wait_for_nominatim()
    results = _get_json(GEOCODING_URL, {"q": city, "format": "json", "limit": 1})
    if not results:
        return None
    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise WeatherUnavailable("Unexpected response from Nominatim") from error


def _fetch_weather(latitude, longitude):
    data = _get_json(WEATHER_URL, {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
    })
    try:
        current = data["current"]
        return {
            "temperature": current["temperature_2m"],  # °C
            "humidity": current["relative_humidity_2m"],  # %
            "wind_speed": current["wind_speed_10m"],  # km/h
            "weather_code": current["weather_code"],  # WMO code, used to pick an icon
        }
    except (KeyError, TypeError) as error:
        raise WeatherUnavailable("Unexpected response from Open-Meteo") from error


def _get_json(url, params):
    try:
        response = requests.get(
            url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise WeatherUnavailable(f"Request to {url} failed") from error


def _wait_for_nominatim():
    # Nominatim allows at most 1 request per second; the lock makes parallel requests queue up
    global _last_nominatim_call
    with _nominatim_lock:
        delay = 1 - (time.monotonic() - _last_nominatim_call)
        if delay > 0:
            time.sleep(delay)
        _last_nominatim_call = time.monotonic()


def _cache_key(city):
    # " Kraków" and "kraków" share one cache entry; quote() keeps the key free of spaces
    return quote(city.strip().lower())