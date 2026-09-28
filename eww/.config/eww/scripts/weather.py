#!/usr/bin/env python3
import urllib.request
import json
import time
import os
import sys

CACHE_FILE = '/tmp/eww_weather_cache.json'
CACHE_TTL = 900  # 15 minutes
GEO_CACHE = '/tmp/eww_geo_cache.json'
GEO_TTL = 86400  # 24 hours

def get_location():
    if os.path.exists(GEO_CACHE):
        try:
            mtime = os.path.getmtime(GEO_CACHE)
            if time.time() - mtime < GEO_TTL:
                with open(GEO_CACHE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

    try:
        req = urllib.request.Request(
            'http://ip-api.com/json/?fields=lat,lon,city,country',
            headers={'User-Agent': 'EwwWeather/1.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            lat = data.get('lat', 55.03)
            lon = data.get('lon', 82.92)
            city = data.get('city', 'Новосибирск')
            loc = {'lat': lat, 'lon': lon, 'city': city}
            with open(GEO_CACHE, 'w', encoding='utf-8') as f:
                json.dump(loc, f, ensure_ascii=False)
            return loc
    except Exception:
        pass

    return {'lat': 55.03, 'lon': 82.92, 'city': 'Новосибирск'}

def get_fallback(city='Новосибирск'):
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        'temp': '--°C',
        'feels_like': '--°C',
        'desc': 'Нет сети',
        'icon': '',
        'humidity': '--%',
        'wind': '-- км/ч',
        'city': city,
        'today_range': '--',
        'tomorrow_temp': '--°C',
        'tomorrow_icon': '',
        'tomorrow_desc': '--'
    }

def decode_wmo(code, is_day):
    if code == 0:
        return ('' if is_day else '', 'Ясно')
    elif code in (1, 2):
        return ('', 'Переменная облачность')
    elif code == 3:
        return ('', 'Пасмурно')
    elif code in (45, 48):
        return ('󰖑', 'Туман')
    elif code in (51, 53, 55):
        return ('󰖗', 'Морось')
    elif code in (56, 57):
        return ('󰖗', 'Ледяная морось')
    elif code in (61, 63, 65):
        return ('󰖖', 'Дождь')
    elif code in (66, 67):
        return ('󰖖', 'Ледяной дождь')
    elif code in (71, 73, 75, 77):
        return ('', 'Снег')
    elif code in (80, 81, 82):
        return ('󰖖', 'Ливень')
    elif code in (85, 86):
        return ('', 'Снегопад')
    elif code in (95, 96, 99):
        return ('', 'Гроза')
    return ('', 'Облачно')

def fetch_weather():
    if os.path.exists(CACHE_FILE):
        mtime = os.path.getmtime(CACHE_FILE)
        if time.time() - mtime < CACHE_TTL:
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

    loc = get_location()
    lat = loc['lat']
    lon = loc['lon']
    city = loc['city']

    url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=2'
    req = urllib.request.Request(url, headers={'User-Agent': 'EwwWeatherWidget/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return get_fallback(city)

    cur = data.get('current', {})
    daily = data.get('daily', {})

    temp = round(cur.get('temperature_2m', 0))
    feels = round(cur.get('apparent_temperature', 0))
    hum = cur.get('relative_humidity_2m', 0)
    wind = round(cur.get('wind_speed_10m', 0))
    is_day = cur.get('is_day', 1)
    code = cur.get('weather_code', 0)

    icon, desc = decode_wmo(code, is_day)

    t_max = round(daily.get('temperature_2m_max', [temp])[0])
    t_min = round(daily.get('temperature_2m_min', [temp])[0])

    tom_max = '--°C'
    tom_icon = ''
    tom_desc = '--'
    if len(daily.get('temperature_2m_max', [])) > 1:
        tom_max = f"{round(daily['temperature_2m_max'][1])}°C"
        tom_code = daily.get('weather_code', [0, 0])[1]
        tom_icon, tom_desc = decode_wmo(tom_code, 1)

    result = {
        'temp': f"{temp}°C",
        'feels_like': f"{feels}°C",
        'desc': desc,
        'icon': icon,
        'humidity': f"{hum}%",
        'wind': f"{wind} км/ч",
        'city': city,
        'today_range': f"{t_min}°..{t_max}°",
        'tomorrow_temp': tom_max,
        'tomorrow_icon': tom_icon,
        'tomorrow_desc': tom_desc
    }

    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False)
    except Exception:
        pass

    return result

if __name__ == '__main__':
    data = fetch_weather()
    print(json.dumps(data, ensure_ascii=False))
