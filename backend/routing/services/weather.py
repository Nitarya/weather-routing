"""Google Weather API client.

The assessment requires a weather lookup at every 10/25/50-mile checkpoint at
that checkpoint's estimated arrival time. Google Weather API is point-based
(one location per request) and returns hourly forecasts in 24-hour pages, so the
client:

* fetches only the pages needed to cover the trip / heatmap window,
* resolves every checkpoint independently (no spatial interpolation), and
* normalizes Google's imperial values into mph / in-per-hour / °F / feet.

Google provides snowfall as liquid-water equivalent (``snowQpf``). The brief's
snow thresholds are snowfall depth, so a documented 10:1 snow ratio is applied.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 25
MAX_WORKERS = 20
PAGE_SIZE = 24
MAX_FORECAST_HOURS = 240
SNOW_LIQUID_TO_DEPTH = 10.0

# Kept for the planner/heatmap call sites; Google returns all needed fields in
# one response, so the variable selection is not used.
DEFAULT_VARIABLES = (
    "wind_speed_10m",
    "precipitation",
    "snowfall",
    "temperature_2m",
    "weather_code",
    "visibility",
)
RISK_VARIABLES = ("wind_speed_10m", "precipitation", "snowfall")


class WeatherError(Exception):
    """Raised when hourly weather data cannot be retrieved."""


_thread_state = threading.local()


def _get_session() -> requests.Session:
    """Keep-alive session per worker to avoid TLS setup on every point/page."""
    session = getattr(_thread_state, "session", None)
    if session is None:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=0)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _thread_state.session = session
    return session


def _get(url: str, params: dict[str, Any]) -> requests.Response:
    return _get_session().get(url, params=params, timeout=REQUEST_TIMEOUT)


def coord_key(lat: float, lng: float) -> str:
    return f"{lat:.4f},{lng:.4f}"


def _api_key() -> str:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise WeatherError(
            "Server is missing GOOGLE_MAPS_API_KEY. Add it to .env and restart the server."
        )
    return settings.GOOGLE_MAPS_API_KEY


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _num(value: Any, default: float = 0.0) -> float:
    return default if value is None else float(value)


def _to_mph(value: float, unit: str) -> float:
    unit = (unit or "").upper()
    if "KILOMETER" in unit:
        return value * 0.621371
    if "METER_PER_SECOND" in unit or unit == "MPS":
        return value * 2.23694
    if "KNOT" in unit:
        return value * 1.15078
    return value


def _to_inches(value: float, unit: str) -> float:
    unit = (unit or "").upper()
    if "MILLIMETER" in unit:
        return value / 25.4
    if "CENTIMETER" in unit:
        return value / 2.54
    return value


def _to_fahrenheit(value: float, unit: str) -> float:
    unit = (unit or "").upper()
    if "CELSIUS" in unit:
        return value * 9 / 5 + 32
    return value


def _to_feet(value: float, unit: str) -> float:
    unit = (unit or "").upper()
    if "MILES" in unit:
        return value * 5280
    if "KILOMETER" in unit:
        return value * 3280.84
    if "METER" in unit:
        return value * 3.28084
    return value


def _condition_meta(condition_type: str) -> tuple[str, str, int]:
    """Map Google's WeatherCondition.Type to (label, icon key, WMO-ish code)."""
    kind = (condition_type or "").upper()
    if kind in {"TYPE_UNSPECIFIED", ""}:
        return "Mixed conditions", "cloudy", 3
    if "THUNDER" in kind or "HAIL" in kind:
        return "Thunderstorm", "storm", 95
    if "SNOW" in kind or "BLIZZARD" in kind or "FLURR" in kind:
        if "HEAVY" in kind or "STORM" in kind:
            return "Heavy snow", "snow", 75
        if "LIGHT" in kind:
            return "Light snow", "snow", 71
        return "Snow", "snow", 73
    if "RAIN" in kind or "SHOWER" in kind or "DRIZZLE" in kind:
        if "HEAVY" in kind or "STORM" in kind:
            return "Heavy rain", "rain", 65
        if "LIGHT" in kind:
            return "Light rain", "rain", 61
        return "Rain", "rain", 63
    if "FOG" in kind or "MIST" in kind:
        return "Fog", "fog", 45
    if "WIND" in kind:
        return "Windy", "windy", 3
    if "CLEAR" in kind:
        return "Clear sky", "clear", 0
    if "PARTLY" in kind:
        return "Partly cloudy", "partly_cloudy", 2
    if "CLOUDY" in kind:
        return "Cloudy", "cloudy", 3
    if "OVERCAST" in kind:
        return "Overcast", "cloudy", 3
    return "Mixed conditions", "cloudy", 3


def _fetch_page(
    lat: float, lng: float, horizon_hours: int, page_token: str | None = None
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "location.latitude": lat,
        "location.longitude": lng,
        "unitsSystem": "IMPERIAL",
        "pageSize": PAGE_SIZE,
        "hours": horizon_hours,
        "languageCode": "en",
        "key": _api_key(),
    }
    if page_token:
        params["pageToken"] = page_token

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = _get(settings.GOOGLE_WEATHER_API_URL, params)
            if response.status_code == 429:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise WeatherError(
                    "Google Weather API is rate-limited. Please try again in a moment."
                )
            if response.status_code in {401, 403}:
                raise WeatherError(
                    "Google Weather API rejected the request. Check that the Weather API "
                    "is enabled and the key is allowed to use it."
                )
            if response.status_code >= 400:
                message = "Google Weather API request failed."
                try:
                    message = response.json().get("error", {}).get("message", message)
                except ValueError:
                    pass
                raise WeatherError(message)
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            logger.warning(
                "Google Weather request failed (attempt %s): %s", attempt + 1, exc
            )
            if attempt < 2:
                time.sleep(0.8 * (attempt + 1))

    raise WeatherError(
        "Google Weather API is unavailable right now. Please try again."
    ) from last_error


def _normalise(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    for entry in entries:
        start = (entry.get("interval") or {}).get("startTime")
        if not start:
            continue
        rows[start] = entry

    ordered = [rows[key] for key in sorted(rows)]
    if not ordered:
        raise WeatherError("Google Weather API returned no hourly forecast data.")

    times: list[datetime] = []
    wind_mph: list[float] = []
    rain_in: list[float] = []
    snow_in: list[float] = []
    temp_f: list[float] = []
    visibility_ft: list[float] = []
    weather_codes: list[float] = []
    conditions: list[str] = []
    condition_keys: list[str] = []

    for entry in ordered:
        interval = entry.get("interval") or {}
        times.append(_parse_time(interval["startTime"]))

        wind = entry.get("wind") or {}
        speed = wind.get("speed") or {}
        wind_mph.append(_to_mph(_num(speed.get("value")), speed.get("unit", "")))

        precipitation = entry.get("precipitation") or {}
        qpf = precipitation.get("qpf") or {}
        rain_in.append(_to_inches(_num(qpf.get("quantity")), qpf.get("unit", "")))
        snow_qpf = precipitation.get("snowQpf") or {}
        snow_liquid = _to_inches(_num(snow_qpf.get("quantity")), snow_qpf.get("unit", ""))
        snow_in.append(snow_liquid * SNOW_LIQUID_TO_DEPTH)

        temperature = entry.get("temperature") or {}
        temp_f.append(
            _to_fahrenheit(_num(temperature.get("degrees")), temperature.get("unit", ""))
        )

        visibility = entry.get("visibility") or {}
        visibility_ft.append(
            _to_feet(_num(visibility.get("distance")), visibility.get("unit", ""))
        )

        condition = entry.get("weatherCondition") or {}
        description = (condition.get("description") or {}).get("text") or ""
        label, key, code = _condition_meta(condition.get("type", ""))
        conditions.append(description or label)
        condition_keys.append(key)
        weather_codes.append(float(code))

    return {
        "times": times,
        "wind_mph": wind_mph,
        "rain_in": rain_in,
        "snow_in": snow_in,
        "temp_f": temp_f,
        "weather_code": weather_codes,
        "visibility_ft": visibility_ft,
        "conditions": conditions,
        "condition_keys": condition_keys,
    }


def _fetch_point(lat: float, lng: float, end: datetime) -> dict[str, Any]:
    now = datetime.now(UTC)
    required_seconds = max(3600.0, (end - now).total_seconds() + 3600.0)
    horizon = min(MAX_FORECAST_HOURS, max(1, math.ceil(required_seconds / 3600.0)))
    if (end - now).total_seconds() > MAX_FORECAST_HOURS * 3600:
        raise WeatherError(
            "Google Weather provides hourly forecasts up to 240 hours ahead. "
            "Choose a departure within the next 8 days."
        )

    entries: list[dict[str, Any]] = []
    token: str | None = None
    pages = 0
    while pages < 10:
        payload = _fetch_page(lat, lng, horizon, token)
        batch = payload.get("forecastHours") or []
        entries.extend(batch)
        pages += 1
        token = payload.get("nextPageToken")
        if not token:
            break
        if batch:
            last_time = _parse_time((batch[-1].get("interval") or {}).get("startTime"))
            if last_time >= end:
                break

    return _normalise(entries)


def fetch_weather(
    points: Iterable[tuple[float, float]],
    start: datetime,
    end: datetime,
    ) -> dict[str, dict[str, Any]]:
    """Fetch Google hourly weather for every checkpoint coordinate.

    Coordinates are intentionally not snapped or interpolated: each sampled
    checkpoint gets its own Google Weather lookup so the 10/25/50-mile sampling
    requirement is preserved. Identical coordinates are only requested once per plan.
    """
    unique: list[tuple[float, float]] = []
    seen: set[str] = set()
    for lat, lng in points:
        key = coord_key(lat, lng)
        if key in seen:
            continue
        seen.add(key)
        unique.append((round(lat, 4), round(lng, 4)))

    if not unique:
        return {}
    if end <= start:
        raise WeatherError("Weather window is invalid.")

    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(unique))) as executor:
        futures = {
            executor.submit(_fetch_point, lat, lng, end): coord_key(lat, lng)
            for lat, lng in unique
        }
        for future, key in futures.items():
            try:
                results[key] = future.result()
            except WeatherError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected Google Weather failure")
                raise WeatherError("Google Weather API failed unexpectedly.") from exc
    return results


def nearest_hour_index(times: Sequence[datetime], target: datetime) -> int | None:
    """Index of the hourly forecast closest to *target*."""
    if not times:
        return None
    target = target.astimezone(UTC)
    nearest = min(
        range(len(times)), key=lambda index: abs((times[index] - target).total_seconds())
    )
    if abs((times[nearest] - target).total_seconds()) > 90 * 60:
        return None
    return nearest


def weather_at(location: dict[str, Any], target: datetime) -> dict[str, Any] | None:
    index = nearest_hour_index(location.get("times", []), target)
    if index is None:
        return None

    def pick(name: str, default: float = 0.0) -> float:
        values = location.get(name) or []
        if index >= len(values) or values[index] is None:
            return default
        return float(values[index])

    conditions = location.get("conditions") or []
    condition_keys = location.get("condition_keys") or []
    condition = conditions[index] if index < len(conditions) else "Mixed conditions"
    condition_key = condition_keys[index] if index < len(condition_keys) else "cloudy"
    visibility_ft = pick("visibility_ft", 52800.0)

    return {
        "wind_mph": round(pick("wind_mph"), 1),
        "rain_in_hr": round(pick("rain_in"), 2),
        "snow_in_hr": round(pick("snow_in"), 2),
        "temp_f": round(pick("temp_f"), 0),
        "visibility_mi": round(visibility_ft / 5280.0, 1),
        "weather_code": int(pick("weather_code", 3)),
        "condition": condition,
        "condition_key": condition_key,
        "forecast_hour": location["times"][index].isoformat(),
    }


def weather_at_offset(
    location: dict[str, Any], start: datetime, hours: int
) -> dict[str, Any] | None:
    return weather_at(location, start + timedelta(hours=hours))
