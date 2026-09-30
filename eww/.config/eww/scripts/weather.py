#!/usr/bin/env python3
import urllib.request
import json
import time
import os
import sys
from pathlib import Path

CONFIG_FILE = os.path.expanduser('~/.config/eww/weather.json')
CACHE_FILE = '/tmp/eww_weather_cache.json'
CACHE_TTL = 600  # 10 minutes

DEFAULT_CONFIG = {
    "city": "Новосибирск",
    "lat": 55.0302,
    "lon": 82.9204,
    "timezone": "Asia/Novosibirsk",
    "auto_geo": False
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return DEFAULT_CONFIG

def get_location():
    cfg = load_config()
    # If auto_geo is False, strictly bypass all network/VPN IP-based geo detection!
    if not cfg.get("auto_geo", False):
        return {
            'lat': cfg.get('lat', 55.0302),
            'lon': cfg.get('lon', 82.9204),
            'city': cfg.get('city', 'Новосибирск'),
            'timezone': cfg.get('timezone', 'Asia/Novosibirsk')
        }

    # Only if auto_geo is explicitly enabled:
    geo_cache = '/tmp/eww_geo_cache.json'
    if os.path.exists(geo_cache):
        try:
            if time.time() - os.path.getmtime(geo_cache) < 86400:
                with open(geo_cache, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

    try:
        req = urllib.request.Request(
            'http://ip-api.com/json/?fields=lat,lon,city,country,timezone',
            headers={'User-Agent': 'EwwWeather/1.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            loc = {
                'lat': data.get('lat', cfg.get('lat', 55.0302)),
                'lon': data.get('lon', cfg.get('lon', 82.9204)),
                'city': data.get('city', cfg.get('city', 'Новосибирск')),
                'timezone': data.get('timezone', cfg.get('timezone', 'Asia/Novosibirsk'))
            }
            with open(geo_cache, 'w', encoding='utf-8') as f:
                json.dump(loc, f, ensure_ascii=False)
            return loc
    except Exception:
        pass

    return {
        'lat': cfg.get('lat', 55.0302),
        'lon': cfg.get('lon', 82.9204),
        'city': cfg.get('city', 'Новосибирск'),
        'timezone': cfg.get('timezone', 'Asia/Novosibirsk')
    }

def get_fallback(city='Новосибирск'):
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['city'] = city
                return data
        except Exception:
            pass
    return {
        'temp': '--°C',
        'temp_num': 0,
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
        return ('' if is_day else '', 'Ясно')
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

def fetch_weather(force_refresh=False):
    if not force_refresh and os.path.exists(CACHE_FILE):
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
    tz = urllib.parse.quote(loc.get('timezone', 'Asia/Novosibirsk'))

    url = (
        f'https://api.open-meteo.com/v1/forecast?'
        f'latitude={lat}&longitude={lon}'
        f'&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m'
        f'&daily=weather_code,temperature_2m_max,temperature_2m_min'
        f'&timezone={tz}&forecast_days=2'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'EwwWeatherWidget/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return get_fallback(city)

    cur = data.get('current', {})
    daily = data.get('daily', {})

    raw_temp = cur.get('temperature_2m', 0)
    raw_feels = cur.get('apparent_temperature', 0)
    temp = round(raw_temp)
    feels = round(raw_feels)
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
        'temp_num': temp,
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
    force = '--force' in sys.argv or '-f' in sys.argv
    data = fetch_weather(force_refresh=force)
    print(json.dumps(data, ensure_ascii=False))
