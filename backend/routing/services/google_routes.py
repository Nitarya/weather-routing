"""Google Routes API client.

Uses the modern ``computeRoutes`` endpoint (legacy Directions API is disabled on
the assessment project).  Requests traffic-aware ETAs and up to three
alternatives; if Google returns fewer than three we ask for toll-free and
highway-free variants to fill out the comparison.
"""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 25
FIELD_MASK = ",".join(
    [
        "routes.duration",
        "routes.staticDuration",
        "routes.distanceMeters",
        "routes.polyline.encodedPolyline",
        "routes.description",
        "routes.routeLabels",
        "routes.viewport",
    ]
)


class RoutingError(Exception):
    """Raised when the routing provider cannot produce usable routes."""


@dataclass
class RouteOption:
    polyline: str
    distance_meters: float
    duration_seconds: float
    static_duration_seconds: float
    description: str = ""
    route_labels: list[str] = field(default_factory=list)
    viewport: dict[str, float] | None = None
    variant: str = "best"

    @property
    def signature(self) -> str:
        return hashlib.sha1(self.polyline.encode()).hexdigest()

    @property
    def distance_miles(self) -> float:
        return self.distance_meters / 1609.344

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60.0


def _parse_duration(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(str(value).rstrip("s"))
    except ValueError:
        return 0.0


def _api_key() -> str:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise RoutingError(
            "Server is missing GOOGLE_MAPS_API_KEY. Add it to .env and restart the server."
        )
    return settings.GOOGLE_MAPS_API_KEY


def _payload(
    origin: dict[str, Any],
    destination: dict[str, Any],
    departure: datetime,
    *,
    avoid_tolls: bool = False,
    avoid_highways: bool = False,
    alternatives: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "origin": {"location": {"latLng": {"latitude": origin["lat"], "longitude": origin["lng"]}}},
        "destination": {
            "location": {"latLng": {"latitude": destination["lat"], "longitude": destination["lng"]}}
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        "departureTime": departure.astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "computeAlternativeRoutes": alternatives,
        "polylineQuality": "HIGH_QUALITY",
        "polylineEncoding": "ENCODED_POLYLINE",
        "languageCode": "en-US",
        "units": "IMPERIAL",
        "routeModifiers": {
            "avoidTolls": avoid_tolls,
            "avoidHighways": avoid_highways,
            "avoidFerries": True,
        },
    }
    return payload


def _call_routes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        response = requests.post(
            settings.GOOGLE_ROUTES_API_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": _api_key(),
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code >= 400:
            message = "Routing request failed."
            try:
                error = response.json().get("error", {})
                message = error.get("message") or message
            except ValueError:
                pass
            raise RoutingError(message)
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Routes API request failed: %s", exc)
        raise RoutingError("Routing service is unavailable. Please try again.") from exc
    return data.get("routes", []) or []


def _to_option(raw: dict[str, Any], variant: str) -> RouteOption | None:
    encoded = (raw.get("polyline") or {}).get("encodedPolyline") or ""
    distance = float(raw.get("distanceMeters") or 0)
    duration = _parse_duration(raw.get("duration"))
    if not encoded or distance <= 0 or duration <= 0:
        return None
    viewport = None
    raw_viewport = raw.get("viewport") or {}
    if raw_viewport.get("low") and raw_viewport.get("high"):
        viewport = {
            "south": float(raw_viewport["low"].get("latitude", 0)),
            "west": float(raw_viewport["low"].get("longitude", 0)),
            "north": float(raw_viewport["high"].get("latitude", 0)),
            "east": float(raw_viewport["high"].get("longitude", 0)),
        }
    return RouteOption(
        polyline=encoded,
        distance_meters=distance,
        duration_seconds=duration,
        static_duration_seconds=_parse_duration(raw.get("staticDuration")) or duration,
        description=raw.get("description") or "",
        route_labels=list(raw.get("routeLabels") or []),
        viewport=viewport,
        variant=variant,
    )


def fetch_routes(
    origin: dict[str, Any],
    destination: dict[str, Any],
    departure: datetime,
) -> list[RouteOption]:
    """Fetch up to three distinct routes, preferring Google's alternatives."""
    try:
        return _fetch_routes(origin, destination, departure)
    except RoutingError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert provider surprises to a clean message
        logger.exception("Unexpected routing failure")
        raise RoutingError("We couldn't build routes for that trip. Please try again.") from exc


def _fetch_routes(
    origin: dict[str, Any],
    destination: dict[str, Any],
    departure: datetime,
) -> list[RouteOption]:
    primary_payload = _payload(origin, destination, departure)
    raw_routes = _call_routes(primary_payload)
    if not raw_routes:
        raise RoutingError(
            "No drivable route was found between those locations. Try a different pair."
        )

    options: list[RouteOption] = []
    seen: set[str] = set()

    def add(raw: dict[str, Any], variant: str) -> None:
        option = _to_option(raw, variant)
        if option is None or option.signature in seen:
            return
        seen.add(option.signature)
        options.append(option)

    for raw in raw_routes:
        add(raw, "best")

    if len(options) < 3:
        # Ask for genuinely different road choices in parallel.
        variants = [
            ("avoid_tolls", {"avoid_tolls": True}),
            ("avoid_highways", {"avoid_highways": True}),
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    _call_routes,
                    _payload(origin, destination, departure, alternatives=False, **flags),
                )
                for _, flags in variants
            ]
            for (variant, _), future in zip(variants, futures, strict=False):
                try:
                    for raw in future.result():
                        add(raw, variant)
                        if len(options) >= 3:
                            break
                except RoutingError as exc:
                    logger.info("Supplementary %s route unavailable: %s", variant, exc)

    # Ensure the shortest-distance route really is represented when Google only
    # offers one option: the trip is still usable with a single route.
    return options[:3]
