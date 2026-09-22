import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

from app_paths import load_config, save_config
from location_win import get_system_location


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
IP_API = "http://ip-api.com/json/"

CACHE_TTL = 6 * 3600   # 定位缓存 6 小时


WMO_CODE = {
    0:  ("晴", "☀️"),
    1:  ("多云转晴", "🌤️"),
    2:  ("多云", "⛅"),
    3:  ("阴", "☁️"),
    45: ("雾", "🌫️"),
    48: ("雾凇", "🌫️"),
    51: ("小毛毛雨", "🌦️"),
    53: ("毛毛雨", "🌦️"),
    55: ("大毛毛雨", "🌧️"),
    61: ("小雨", "🌦️"),
    63: ("中雨", "🌧️"),
    65: ("大雨", "🌧️"),
    71: ("小雪", "🌨️"),
    73: ("中雪", "🌨️"),
    75: ("大雪", "❄️"),
    77: ("雪粒", "🌨️"),
    80: ("阵雨", "🌦️"),
    81: ("强阵雨", "🌧️"),
    82: ("暴雨", "⛈️"),
    85: ("阵雪", "🌨️"),
    86: ("强阵雪", "❄️"),
    95: ("雷阵雨", "⛈️"),
    96: ("雷阵雨伴冰雹", "⛈️"),
    99: ("强雷暴伴冰雹", "⛈️"),
}


@dataclass
class Weather:
    city: str
    temperature: float
    code: int
    desc: str
    icon: str
    wind: float
    humidity: int


def _get_json(url: str, params: dict, timeout: int = 8) -> dict:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{qs}",
        headers={"User-Agent": "MyToolbox/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------- 定位 ----------
def geocode(city: str) -> Optional[tuple[float, float, str]]:
    data = _get_json(GEOCODE_URL, {
        "name": city, "count": 1, "language": "zh", "format": "json",
    })
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    return r["latitude"], r["longitude"], r.get("name", city)


def locate_by_ip() -> Optional[tuple[float, float, str]]:
    try:
        data = _get_json(IP_API, {
            "fields": "status,country,regionName,city,lat,lon",
            "lang": "zh-CN",
        }, timeout=6)
    except Exception:
        return None
    if data.get("status") != "success":
        return None
    return data["lat"], data["lon"], data.get("city") or data.get("regionName") or "本地"


def reverse_city(lat: float, lon: float) -> Optional[str]:
    """用 ip-api 反查城市名（它支持 lat/lon）"""
    try:
        data = _get_json(IP_API, {
            "fields": "status,city,regionName",
            "lang": "zh-CN",
            "lat": lat, "lon": lon,
        }, timeout=6)
    except Exception:
        return None
    if data.get("status") != "success":
        return None
    return data.get("city") or data.get("regionName")


def _load_cached_location():
    cfg = load_config()
    cache = cfg.get("weather_cache")
    if not cache:
        return None
    if time.time() - cache.get("ts", 0) > CACHE_TTL:
        return None
    return cache.get("lat"), cache.get("lon"), cache.get("city", "本地")


def _save_cached_location(lat: float, lon: float, city: str):
    cfg = load_config()
    cfg["weather_cache"] = {"lat": lat, "lon": lon, "city": city, "ts": time.time()}
    save_config(cfg)


def resolve_location() -> tuple[float, float, str]:
    """
    三级回退：缓存 → 系统定位 → IP 定位 → 默认北京
    返回 (纬度, 经度, 城市名)
    """
    # 0) 缓存
    cached = _load_cached_location()
    if cached:
        return cached

    # 1) 系统定位
    pos = get_system_location()
    if pos:
        lat, lon = pos
        city = reverse_city(lat, lon) or "本地"
        _save_cached_location(lat, lon, city)
        return lat, lon, city

    # 2) IP 定位
    ip_loc = locate_by_ip()
    if ip_loc:
        lat, lon, city = ip_loc
        _save_cached_location(lat, lon, city)
        return lat, lon, city

    # 3) 默认
    return 39.9042, 116.4074, "北京"


# ---------- 天气 ----------
def fetch_weather(city: str = "", lat: float = None, lon: float = None) -> Weather:
    if lat is None or lon is None:
        loc = geocode(city)
        if not loc:
            raise ValueError(f"找不到城市：{city}")
        lat, lon, name = loc
    else:
        name = city or "本地"

    data = _get_json(WEATHER_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    })
    cur = data.get("current") or {}
    code = int(cur.get("weather_code", 0))
    desc, icon = WMO_CODE.get(code, ("未知", "❓"))

    return Weather(
        city=name,
        temperature=float(cur.get("temperature_2m", 0)),
        code=code, desc=desc, icon=icon,
        wind=float(cur.get("wind_speed_10m", 0)),
        humidity=int(cur.get("relative_humidity_2m", 0)),
    )


def fetch_weather_auto(city_override: str = "") -> Weather:
    """city_override 非空则用它，否则自动定位"""
    if city_override:
        return fetch_weather(city_override)
    lat, lon, city = resolve_location()
    return fetch_weather(city, lat, lon)