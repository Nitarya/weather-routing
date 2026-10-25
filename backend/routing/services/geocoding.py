"""Google Geocoding client used by the planning endpoint."""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


class LocationError(Exception):
    """Raised when a location cannot be resolved."""


def _api_key() -> str:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise LocationError(
            "Server is missing GOOGLE_MAPS_API_KEY. Add it to .env and restart the server."
        )
    return settings.GOOGLE_MAPS_API_KEY


def _components(result: dict[str, Any]) -> dict[str, str]:
    parts = {"city": "", "state": "", "country": ""}
    for component in result.get("address_components", []):
        types = set(component.get("types", []))
        short = component.get("short_name", "")
        long = component.get("long_name", "")
        if "locality" in types or "postal_town" in types:
            parts["city"] = long
        elif "administrative_area_level_1" in types:
            parts["state"] = short
        elif "country" in types:
            parts["country"] = short
    return parts


def geocode_address(query: str) -> dict[str, Any]:
    query = " ".join((query or "").split())
    if not query:
        raise LocationError("Origin and destination are required.")

    try:
        response = requests.get(
            settings.GOOGLE_GEOCODE_API_URL,
            params={"address": query, "key": _api_key(), "language": "en", "region": "us"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Geocoding request failed: %s", exc)
        raise LocationError("Geocoding service is unavailable. Please try again.") from exc

    status = payload.get("status")
    if status == "ZERO_RESULTS":
        raise LocationError(f'No location found for "{query}".')
    if status != "OK" or not payload.get("results"):
        message = payload.get("error_message") or status or "Unknown geocoding error"
        logger.warning("Geocoding error: %s", message)
        raise LocationError(f'No location found for "{query}".')

    result = payload["results"][0]
    location = (result.get("geometry") or {}).get("location") or {}
    components = _components(result)
    label = result.get("formatted_address") or query
    return {
        "label": label,
        "primary": components["city"] or label,
        "secondary": ", ".join(
            part for part in (components["city"], components["state"], components["country"]) if part
        ),
        "lat": float(location.get("lat", 0.0)),
        "lng": float(location.get("lng", 0.0)),
        "city": components["city"],
        "state": components["state"],
        "country": components["country"],
    }


def resolve_location(value: Any) -> dict[str, Any]:
    if isinstance(value, str) and value.strip():
        return geocode_address(value)
    raise LocationError("Origin and destination are required.")

def reverse_geocode(lat: float, lng: float) -> str:
    """Return a human-readable city/county/state label for a checkpoint."""
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise LocationError("Coordinates are outside the valid range.")

    try:
        response = requests.get(
            settings.GOOGLE_GEOCODE_API_URL,
            params={
                "latlng": f"{lat:.6f},{lng:.6f}",
                "key": _api_key(),
                "language": "en",
                "result_type": (
                    "locality|postal_town|sublocality|"
                    "administrative_area_level_3|administrative_area_level_2|"
                    "administrative_area_level_1"
                ),
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Reverse geocoding failed: %s", exc)
        raise LocationError("Could not resolve the checkpoint area.") from exc

    status = payload.get("status")
    if status == "ZERO_RESULTS":
        return ""
    if status != "OK" or not payload.get("results"):
        logger.warning("Reverse geocoding error: %s", status)
        raise LocationError("Could not resolve the checkpoint area.")

    for result in payload["results"]:
        city = county = state = state_long = ""
        for component in result.get("address_components", []):
            types = set(component.get("types", []))
            long_name = component.get("long_name", "")
            short_name = component.get("short_name", "")
            if types & {"locality", "postal_town", "sublocality"}:
                city = city or long_name
            elif "administrative_area_level_2" in types:
                county = county or long_name
            elif "administrative_area_level_1" in types:
                state = state or short_name
                state_long = state_long or long_name
        if city:
            return f"{city}, {state}" if state else city
        if county:
            return f"{county}, {state}" if state else county
        if state:
            return state_long or state

    return payload["results"][0].get("formatted_address", "")

