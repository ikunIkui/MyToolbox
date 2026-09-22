"""Windows 系统定位（可选）。失败返回 None，不抛异常。"""

import asyncio

try:
    from winsdk.windows.devices.geolocation import (
        Geolocator, GeolocationAccessStatus,
    )
    HAS_WINSDK = True
except Exception:
    HAS_WINSDK = False


async def _get_pos_async(timeout: float = 8.0):
    access = await Geolocator.request_access_async()
    if access != GeolocationAccessStatus.ALLOWED:
        return None
    locator = Geolocator()
    pos = await asyncio.wait_for(locator.get_geoposition_async(), timeout=timeout)
    if not pos:
        return None
    c = pos.coordinate
    return c.latitude, c.longitude


def get_system_location():
    """返回 (纬度, 经度) 或 None"""
    if not HAS_WINSDK:
        return None
    try:
        return asyncio.run(_get_pos_async())
    except Exception:
        return None