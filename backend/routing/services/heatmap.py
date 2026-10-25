"""Corridor forecast heatmap for the selected route."""

from __future__ import annotations

import logging
import math
from datetime import timedelta
from typing import Any

from django.conf import settings

from .planner import PlanValidationError, parse_departure
from .polyline import (
    RoutePoint,
    bearing_between,
    cumulative_distances,
    decode_polyline,
    interpolate,
    offset_point,
)
from .risk import LEVEL_RANK, LEVELS, NO_TRAVEL, assess_weather
from .weather import WeatherError, coord_key, fetch_weather, nearest_hour_index

logger = logging.getLogger(__name__)

MAX_CELLS = 160
MIN_SPACING = 9.0
START_SPACING = 30.0


class HeatmapError(Exception):
    """Raised when corridor forecast data cannot be built."""


def _corridor_cells(
    points: list[RoutePoint], total_miles: float, spacing: float
) -> list[RoutePoint]:
    mid_lat = sum(point.lat for point in points) / len(points)
    lat_step = spacing / 69.0
    lng_step = spacing / (69.0 * max(0.2, math.cos(math.radians(mid_lat))))
    anchor_distance = max(3.0, spacing / 2)
    cumulative = cumulative_distances(points)

    anchors: list[tuple[RoutePoint, float]] = []
    mile = 0.0
    while mile <= total_miles:
        anchors.append((interpolate(points, cumulative, mile), mile))
        mile += anchor_distance
    if not anchors or anchors[-1][1] < total_miles:
        anchors.append((points[-1], total_miles))

    lateral_offsets = [
        -1.35 * spacing,
        -0.9 * spacing,
        -0.45 * spacing,
        0.0,
        0.45 * spacing,
        0.9 * spacing,
        1.35 * spacing,
    ]

    cells: dict[tuple[int, int], RoutePoint] = {}
    for index, (anchor, _) in enumerate(anchors):
        next_point = anchors[min(index + 1, len(anchors) - 1)][0]
        previous_point = anchors[max(0, index - 1)][0]
        if abs(next_point.lat - anchor.lat) + abs(next_point.lng - anchor.lng) < 1e-9:
            bearing = bearing_between(previous_point, anchor)
        else:
            bearing = bearing_between(anchor, next_point)
        for offset in lateral_offsets:
            displaced = offset_point(anchor, bearing + 90, offset)
            key = (round(displaced.lat / lat_step), round(displaced.lng / lng_step))
            cells[key] = RoutePoint(lat=key[0] * lat_step, lng=key[1] * lng_step)

    for point in (points[0], points[-1]):
        key = (round(point.lat / lat_step), round(point.lng / lng_step))
        cells.setdefault(key, RoutePoint(lat=key[0] * lat_step, lng=key[1] * lng_step))
    return list(cells.values())


def _build_cells(points: list[RoutePoint], total_miles: float) -> tuple[list[RoutePoint], float]:
    spacing = START_SPACING
    cells: list[RoutePoint] = []
    while spacing >= MIN_SPACING:
        cells = _corridor_cells(points, total_miles, spacing)
        if len(cells) <= MAX_CELLS:
            break
        spacing *= 1.18
    return cells, round(spacing, 1)


def build_heatmap(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = payload.get("polyline")
    if not isinstance(encoded, str) or len(encoded) < 8:
        raise PlanValidationError("A route polyline is required for the heatmap.")

    try:
        load_lb = float(payload.get("load_lb", 0))
    except (TypeError, ValueError) as exc:
        raise PlanValidationError("Load weight must be a number.") from exc
    if not (0 <= load_lb <= 200_000):
        raise PlanValidationError("Load weight must be between 0 and 200,000 lb.")

    departure, warnings = parse_departure(payload.get("departure_time"))
    hours = int(min(72, max(1, payload.get("hours", settings.FORECAST_HOURS))))

    try:
        points = decode_polyline(encoded)
    except (IndexError, ValueError) as exc:
        raise PlanValidationError("The route geometry could not be decoded.") from exc
    if len(points) < 2:
        raise PlanValidationError("The route geometry is incomplete.")

    total_miles = cumulative_distances(points)[-1]
    if total_miles < 3:
        raise PlanValidationError("The route is too short to build a heatmap.")

    cells, spacing = _build_cells(points, total_miles)
    if not cells:
        raise HeatmapError("Could not build a corridor for this route.")

    end = departure + timedelta(hours=hours + 2)
    try:
        weather_by_point = fetch_weather(
            [(cell.lat, cell.lng) for cell in cells], departure, end
        )
    except WeatherError as exc:
        raise HeatmapError(str(exc)) from exc

    hours_iso = [
        (departure + timedelta(hours=offset)).isoformat().replace("+00:00", "Z")
        for offset in range(hours + 1)
    ]

    cell_payloads: list[dict[str, Any]] = []
    level_counts = [{level: 0 for level in LEVELS} for _ in range(hours + 1)]
    for cell in cells:
        location = weather_by_point.get(coord_key(cell.lat, cell.lng))
        if not location or not location.get("times"):
            continue
        base_index = nearest_hour_index(location["times"], departure) or 0
        risks: list[int] = []
        for offset in range(hours + 1):
            index = min(base_index + offset, len(location["times"]) - 1)
            assessment = assess_weather(
                wind_mph=location["wind_mph"][index] or 0.0,
                rain_in_hr=location["rain_in"][index] or 0.0,
                snow_in_hr=location["snow_in"][index] or 0.0,
                load_lb=load_lb,
            )
            code = LEVEL_RANK[assessment.level]
            risks.append(code)
            level_counts[offset][assessment.level] += 1
        cell_payloads.append(
            {"lat": round(cell.lat, 4), "lng": round(cell.lng, 4), "risks": risks}
        )

    if not cell_payloads:
        raise HeatmapError("Weather data was unavailable for this corridor.")

    summary = []
    for offset in range(hours + 1):
        counts = level_counts[offset]
        highest = max(
            (level for level in LEVELS if counts[level] > 0),
            key=lambda level: LEVEL_RANK[level],
            default="low",
        )
        summary.append(
            {
                "hour": offset,
                "time": hours_iso[offset],
                "highest_level": highest,
                "counts": counts,
                "no_travel_cells": counts[NO_TRAVEL],
            }
        )

    return {
        "hours": hours_iso,
        "cells": cell_payloads,
        "summary": summary,
        "spacing_miles": spacing,
        "route_miles": round(total_miles, 1),
        "cell_count": len(cell_payloads),
        "warnings": warnings,
        "meta": {
            "weather_source": "Google Weather API hourly forecast",
            "forecast_hours": hours,
            "weather_points": len(cell_payloads),
        },
    }
