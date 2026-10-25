"""Polyline decoding and distance helpers (no external geo dependencies)."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_MILES = 3958.7613


@dataclass(frozen=True)
class RoutePoint:
    lat: float
    lng: float


@dataclass(frozen=True)
class RouteSample:
    mile: float
    lat: float
    lng: float
    fraction: float


def decode_polyline(encoded: str) -> list[RoutePoint]:
    """Decode a Google encoded polyline (precision 5)."""
    points: list[RoutePoint] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lat = ~(result >> 1) if result & 1 else result >> 1
        lat += delta_lat

        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lng = ~(result >> 1) if result & 1 else result >> 1
        lng += delta_lng

        points.append(RoutePoint(lat=lat / 1e5, lng=lng / 1e5))

    return points


def haversine_miles(a: RoutePoint | tuple[float, float], b: RoutePoint | tuple[float, float]) -> float:
    lat1, lng1 = (a.lat, a.lng) if isinstance(a, RoutePoint) else a
    lat2, lng2 = (b.lat, b.lng) if isinstance(b, RoutePoint) else b
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = radians(lng2 - lng1)
    h = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * asin(sqrt(min(1.0, h)))


def cumulative_distances(points: list[RoutePoint]) -> list[float]:
    distances = [0.0]
    total = 0.0
    for previous, current in zip(points, points[1:], strict=False):
        total += haversine_miles(previous, current)
        distances.append(total)
    return distances


def interpolate(points: list[RoutePoint], cumulative: list[float], target_mile: float) -> RoutePoint:
    """Return the point at *target_mile* along a route (linear between vertices)."""
    if not points:
        raise ValueError("Cannot interpolate an empty route")
    if target_mile <= 0:
        return points[0]
    if target_mile >= cumulative[-1]:
        return points[-1]

    # Polyline vertex counts are small; bisect keeps this O(log n).
    low, high = 0, len(cumulative) - 1
    while low < high:
        mid = (low + high) // 2
        if cumulative[mid] < target_mile:
            low = mid + 1
        else:
            high = mid
    index = max(1, low)
    segment_start = cumulative[index - 1]
    segment_length = max(1e-9, cumulative[index] - segment_start)
    ratio = (target_mile - segment_start) / segment_length
    start, end = points[index - 1], points[index]
    return RoutePoint(
        lat=start.lat + (end.lat - start.lat) * ratio,
        lng=start.lng + (end.lng - start.lng) * ratio,
    )


def sample_route(points: list[RoutePoint], interval_miles: float) -> tuple[list[RouteSample], float]:
    """Sample a route at a fixed mile interval, always including both endpoints."""
    if len(points) < 2:
        raise ValueError("A route needs at least two points")
    cumulative = cumulative_distances(points)
    total = cumulative[-1]
    if total <= 0:
        raise ValueError("Route has zero length")

    targets: list[float] = []
    mile = 0.0
    while mile < total:
        targets.append(mile)
        mile += interval_miles
    # Avoid a tiny final stub; append the exact destination otherwise.
    if total - targets[-1] >= max(1.0, interval_miles * 0.25):
        targets.append(total)
    else:
        targets[-1] = total

    samples = [
        RouteSample(
            mile=mile,
            lat=(point := interpolate(points, cumulative, mile)).lat,
            lng=point.lng,
            fraction=mile / total,
        )
        for mile in targets
    ]
    return samples, total


def bounding_box(points: list[RoutePoint]) -> dict[str, float]:
    lats = [point.lat for point in points]
    lngs = [point.lng for point in points]
    return {
        "north": max(lats),
        "south": min(lats),
        "east": max(lngs),
        "west": min(lngs),
    }


def offset_point(point: RoutePoint, bearing_degrees: float, distance_miles: float) -> RoutePoint:
    """Move a point by *distance_miles* along a bearing (flat-earth approximation)."""
    bearing = radians(bearing_degrees)
    northing = cos(bearing) * distance_miles
    easting = sin(bearing) * distance_miles
    lat = point.lat + northing / 69.0
    lng = point.lng + easting / (69.0 * max(0.2, cos(radians(point.lat))))
    return RoutePoint(lat=lat, lng=lng)


def bearing_between(a: RoutePoint, b: RoutePoint) -> float:
    from math import atan2, degrees

    d_lng = radians(b.lng - a.lng) * cos(radians((a.lat + b.lat) / 2))
    d_lat = radians(b.lat - a.lat)
    return (degrees(atan2(d_lng, d_lat)) + 360) % 360
