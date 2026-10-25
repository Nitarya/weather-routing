"""Route planning orchestration: routing → checkpoint sampling → risk → ranking."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from django.conf import settings

from .geocoding import LocationError, resolve_location
from .google_routes import RouteOption, RoutingError, fetch_routes
from .polyline import (
    bounding_box,
    decode_polyline,
    haversine_miles,
    sample_route,
)
from .risk import (
    HIGH,
    LEVEL_LABEL,
    LEVEL_RANK,
    LEVEL_SCORE,
    LEVELS,
    LOW,
    MODERATE,
    NO_TRAVEL,
    SEVERE,
    assess_weather,
)
from .weather import WeatherError, coord_key, fetch_weather, weather_at

logger = logging.getLogger(__name__)


class PlanValidationError(Exception):
    """User input is invalid (HTTP 400)."""


class PlannerError(Exception):
    """An upstream service failed in a way we can explain (HTTP 502)."""


@dataclass
class PlannedRoute:
    option: RouteOption
    route_id: str
    checkpoints: list[dict[str, Any]]
    risk: dict[str, Any]

    @property
    def is_safe(self) -> bool:
        return self.risk["no_travel_miles"] == 0 and self.risk["severe_miles"] == 0


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_departure(value: Any) -> tuple[datetime, list[str]]:
    warnings: list[str] = []
    if not isinstance(value, str) or not value.strip():
        raise PlanValidationError("Choose a departure date and time.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise PlanValidationError("Departure time must be a valid ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise PlanValidationError("Departure time must include a timezone offset.")

    now = datetime.now(UTC)
    departure = parsed.astimezone(UTC)
    if departure < now - timedelta(minutes=5):
        departure = now + timedelta(minutes=5)
        warnings.append("Departure was in the past; using the next available forecast window.")
    if departure > now + timedelta(days=7):
        raise PlanValidationError(
            "Departure must be within the next 7 days so hourly Google Weather forecasts "
            "are available."
        )
    return departure, warnings


def _route_id(option: RouteOption) -> str:
    digest = hashlib.sha1(
        f"{option.polyline}:{option.duration_seconds}".encode()
    ).hexdigest()[:10]
    return f"route-{digest}"


def _trapezoid_weights(checkpoints: list[dict[str, Any]]) -> list[float]:
    """Give interior checkpoints a full segment's worth of exposure.

    The first/last checkpoints receive half of their adjacent segment, so the
    weights always sum to the route length.  This lets us report distance at
    each risk level without pretending a checkpoint only covers the distance to
    the *previous* sample.
    """
    if len(checkpoints) < 2:
        return [1.0] * len(checkpoints)
    segments = [
        max(0.0, checkpoints[index + 1]["mile"] - checkpoints[index]["mile"])
        for index in range(len(checkpoints) - 1)
    ]
    weights: list[float] = []
    for index in range(len(checkpoints)):
        previous = segments[index - 1] if index > 0 else 0.0
        following = segments[index] if index < len(segments) else 0.0
        weights.append(previous / 2 + following / 2)
    return weights


def _summarise_risk(checkpoints: list[dict[str, Any]], distance_miles: float) -> dict[str, Any]:
    weights = _trapezoid_weights(checkpoints)
    by_level = {level: 0.0 for level in LEVELS}
    score_total = 0.0
    exposed_miles = 0.0
    counts = {level: 0 for level in LEVELS}

    for checkpoint, weight in zip(checkpoints, weights, strict=False):
        level = checkpoint["risk"]["level"]
        by_level[level] += weight
        score_total += weight * LEVEL_SCORE[level]
        counts[level] += 1
        exposed_miles += weight

    if exposed_miles <= 0:
        exposed_miles = distance_miles or 1.0
    average = score_total / exposed_miles

    # No Travel is worse than Severe. Treat both as "severe-weather miles" for
    # the primary recommendation criterion, while reporting them separately.
    severe_miles = by_level[SEVERE] + by_level[NO_TRAVEL]
    max_level = max((level for level in LEVELS if counts[level] > 0), key=LEVEL_RANK.__getitem__)

    return {
        "level": max_level,
        "label": LEVEL_LABEL[max_level],
        "score": LEVEL_SCORE[max_level],
        "avg_risk": round(average, 2),
        "severe_miles": round(severe_miles, 1),
        "high_miles": round(by_level[HIGH], 1),
        "moderate_miles": round(by_level[MODERATE], 1),
        "low_miles": round(by_level[LOW], 1),
        "no_travel_miles": round(by_level[NO_TRAVEL], 1),
        "miles": {
            level: round(by_level[level], 1)
            for level in LEVELS
            if by_level[level] > 0
        },
        "counts": counts,
        "checkpoint_count": len(checkpoints),
        "risk_score_avg": round(average, 3),
    }


def _build_checkpoints(
    option: RouteOption,
    departure: datetime,
    interval_miles: int,
    load_lb: float,
    weather_by_point: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    points = decode_polyline(option.polyline)
    samples, total_miles = sample_route(points, interval_miles)
    duration_seconds = option.duration_seconds
    checkpoints: list[dict[str, Any]] = []
    previous_mile = 0.0

    for index, sample in enumerate(samples):
        eta = departure + timedelta(seconds=duration_seconds * sample.fraction)
        location = weather_by_point.get(coord_key(sample.lat, sample.lng))
        if location is None:
            raise PlannerError("Weather data was incomplete for one of the routes.")
        condition = weather_at(location, eta)
        if condition is None:
            raise PlannerError(
                "The hourly forecast does not reach this route's arrival time. "
                "Try a departure within the next couple of days."
            )

        assessment = assess_weather(
            wind_mph=condition["wind_mph"],
            rain_in_hr=condition["rain_in_hr"],
            snow_in_hr=condition["snow_in_hr"],
            load_lb=load_lb,
        )
        checkpoints.append(
            {
                "index": index,
                "mile": round(sample.mile, 1),
                "distance_from_prev_miles": round(sample.mile - previous_mile, 1),
                "lat": round(sample.lat, 5),
                "lng": round(sample.lng, 5),
                "eta": _iso(eta),
                "risk": assessment.as_dict(),
                "weather": condition,
            }
        )
        previous_mile = sample.mile

    return checkpoints, total_miles


def _route_sort_key(route: PlannedRoute) -> tuple[float, float, float, float, float]:
    risk = route.risk
    return (
        risk["severe_miles"],
        risk["high_miles"],
        risk["risk_score_avg"],
        route.option.duration_seconds,
        route.option.distance_meters,
    )


def _recommendation_reason(winner: PlannedRoute, routes: list[PlannedRoute]) -> str:
    others = [route for route in routes if route is not winner]
    parts: list[str] = []
    risk = winner.risk

    if risk["severe_miles"] == 0:
        parts.append("zero severe-weather miles")
    else:
        parts.append(f"{risk['severe_miles']:.0f} severe-weather mi (fewest)")

    if others:
        tied_or_worse = all(risk["high_miles"] <= other.risk["high_miles"] for other in others)
        if risk["high_miles"] == 0:
            parts.append("no high-risk mileage")
        elif tied_or_worse:
            parts.append(f"{risk['high_miles']:.0f} high-risk mi (fewest)")

    if all(risk["risk_score_avg"] <= other.risk["risk_score_avg"] for other in others):
        parts.append(f"lowest average risk ({risk['risk_score_avg']:.2f})")

    if others:
        fastest = min(routes, key=lambda route: route.option.duration_seconds)
        if fastest is winner:
            parts.append("fastest ETA")
        else:
            delay = round((winner.option.duration_seconds - fastest.option.duration_seconds) / 60)
            if delay <= 5:
                parts.append("within 5 min of the fastest route")

    return "Recommended because it has " + ", ".join(parts) + "."


def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise PlannerError(
            "Server is missing GOOGLE_MAPS_API_KEY. Add it to .env and restart the server."
        )

    try:
        load_lb = float(payload.get("load_lb", 0))
    except (TypeError, ValueError) as exc:
        raise PlanValidationError("Load weight must be a number.") from exc
    if not (0 <= load_lb <= 200_000):
        raise PlanValidationError("Load weight must be between 0 and 200,000 lb.")

    try:
        interval = int(payload.get("sample_interval_miles", 25))
    except (TypeError, ValueError) as exc:
        raise PlanValidationError("Sample interval must be 10, 25 or 50 miles.") from exc
    if interval not in settings.SAMPLE_INTERVALS:
        raise PlanValidationError("Sample interval must be 10, 25 or 50 miles.")

    departure, warnings = parse_departure(payload.get("departure_time"))
    origin_raw = payload.get("origin")
    destination_raw = payload.get("destination")
    if not origin_raw or not destination_raw:
        raise PlanValidationError("Origin and destination are required.")

    try:
        origin = resolve_location(origin_raw)
        destination = resolve_location(destination_raw)
    except LocationError as exc:
        raise PlanValidationError(str(exc)) from exc

    if haversine_miles((origin["lat"], origin["lng"]), (destination["lat"], destination["lng"])) < 1:
        raise PlanValidationError("Origin and destination are too close to route between.")

    try:
        options = fetch_routes(origin, destination, departure)
    except RoutingError as exc:
        raise PlannerError(str(exc)) from exc

    if not options:
        raise PlannerError("No routes were returned for that trip.")

    # Sample checkpoints first so all weather can be fetched in parallel batches.
    sampled_routes: list[tuple[RouteOption, list[Any], float]] = []
    all_points: list[tuple[float, float]] = []
    for option in options:
        try:
            points = decode_polyline(option.polyline)
            samples, total = sample_route(points, interval)
        except ValueError as exc:
            logger.warning("Skipping malformed route: %s", exc)
            continue
        sampled_routes.append((option, samples, total))
        all_points.extend((sample.lat, sample.lng) for sample in samples)

    if not sampled_routes:
        raise PlannerError("The routing provider returned unusable route geometry.")

    latest_arrival = departure + timedelta(
        seconds=max(option.duration_seconds for option in options)
    )
    weather_start = departure - timedelta(hours=1)
    weather_end = latest_arrival + timedelta(hours=2)
    try:
        weather_by_point = fetch_weather(all_points, weather_start, weather_end)
    except WeatherError as exc:
        raise PlannerError(str(exc)) from exc

    planned: list[PlannedRoute] = []
    for option, _samples, total_miles in sampled_routes:
        checkpoints, _ = _build_checkpoints(
            option, departure, interval, load_lb, weather_by_point
        )
        risk = _summarise_risk(checkpoints, total_miles)
        planned.append(
            PlannedRoute(
                option=option,
                route_id=_route_id(option),
                checkpoints=checkpoints,
                risk=risk,
            )
        )

    # Stable, unique route IDs even when two options are extremely similar.
    used_ids: set[str] = set()
    for planned_route in planned:
        candidate = planned_route.route_id
        suffix = 2
        while candidate in used_ids:
            candidate = f"{planned_route.route_id}-{suffix}"
            suffix += 1
        planned_route.route_id = candidate
        used_ids.add(candidate)

    ranked = sorted(planned, key=_route_sort_key)
    rank_by_id = {route.route_id: index + 1 for index, route in enumerate(ranked)}
    winner = ranked[0]
    fastest_id = min(planned, key=lambda route: route.option.duration_seconds).route_id

    letters = "ABCDEFGH"
    routes_payload: list[dict[str, Any]] = []
    # Present routes in recommendation order and letter them A, B, C so the
    # safest option is always the first card the driver sees.
    for route in ranked:
        option = route.option
        rank = rank_by_id[route.route_id]
        tags: list[str] = []
        if rank == 1:
            tags.append("Recommended")
        if route.route_id == fastest_id:
            tags.append("Fastest")
        if (
            route.risk["counts"]["no_travel"] == 0
            and route.risk["counts"]["severe"] == 0
            and route.risk["counts"]["high"] == 0
        ):
            tags.append("All-clear")

        eta = departure + timedelta(seconds=option.duration_seconds)
        points = decode_polyline(option.polyline)
        routes_payload.append(
            {
                "id": route.route_id,
                "name": f"Route {letters[rank - 1]}",
                "description": option.description or "Truck route",
                "tags": tags,
                "rank": rank,
                "is_recommended": rank == 1,
                "distance_miles": round(option.distance_miles, 1),
                "duration_minutes": round(option.duration_seconds / 60),
                "static_duration_minutes": round(option.static_duration_seconds / 60),
                "traffic_delay_minutes": max(
                    0, round((option.duration_seconds - option.static_duration_seconds) / 60)
                ),
                "eta": _iso(eta),
                "polyline": option.polyline,
                "bounds": bounding_box(points),
                "checkpoints": route.checkpoints,
                "risk": route.risk,
            }
        )

    result = {
        "generated_at": _iso(datetime.now(UTC)),
        "request": {
            "origin": origin,
            "destination": destination,
            "departure_time": _iso(departure),
            "load_lb": round(load_lb),
            "sample_interval_miles": interval,
        },
        "origin": origin,
        "destination": destination,
        "departure_time": _iso(departure),
        "load_lb": round(load_lb),
        "sample_interval_miles": interval,
        "routes": routes_payload,
        "recommendation": {
            "route_id": winner.route_id,
            "reason": _recommendation_reason(winner, planned),
            "ranked_route_ids": [route.route_id for route in ranked],
            "criteria": [
                "Fewest severe-weather miles (includes No Travel)",
                "Fewest high-risk miles",
                "Lowest distance-weighted average risk",
                "Shortest travel time",
            ],
            "ranking": [
                {
                    "route_id": route.route_id,
                    "rank": rank_by_id[route.route_id],
                    "severe_miles": route.risk["severe_miles"],
                    "high_miles": route.risk["high_miles"],
                    "avg_risk": route.risk["avg_risk"],
                    "duration_minutes": round(route.option.duration_seconds / 60),
                }
                for route in ranked
            ],
        },
        "warnings": warnings
        + (
            [f"Only {len(planned)} distinct route(s) were available for this trip."]
            if len(planned) < 3
            else []
        )
        + (
            ["This trip has at least one No Travel checkpoint. Consider delaying departure."]
            if any(route.risk["no_travel_miles"] > 0 for route in planned)
            else []
        ),
        "meta": {
            "routing_source": "Google Routes API",
            "weather_source": "Google Weather API hourly forecast",
            "route_count": len(planned),
            "weather_points": len(all_points),
            "forecast_hours": settings.FORECAST_HOURS,
        },
    }

    return result
