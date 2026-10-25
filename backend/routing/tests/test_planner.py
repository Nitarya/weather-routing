from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase

from routing.services import planner
from routing.services.google_routes import RouteOption
from routing.services.planner import (
    PlannedRoute,
    _route_sort_key,
    _summarise_risk,
    build_plan,
)
from routing.services.polyline import RoutePoint
from routing.services.weather import coord_key


def encode_polyline(points: list[RoutePoint]) -> str:
    """Minimal encoder used only by tests."""
    output: list[str] = []
    previous_lat = 0
    previous_lng = 0

    def encode_value(value: int) -> None:
        value = ~(value << 1) if value < 0 else (value << 1)
        while value >= 0x20:
            output.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        output.append(chr(value + 63))

    for point in points:
        lat = round(point.lat * 1e5)
        lng = round(point.lng * 1e5)
        encode_value(lat - previous_lat)
        encode_value(lng - previous_lng)
        previous_lat, previous_lng = lat, lng
    return "".join(output)


def synthetic_route(offset: float, count: int = 41) -> str:
    points = []
    for index in range(count):
        t = index / (count - 1)
        lat = 32.7767 + (39.7392 - 32.7767) * t + offset * math.sin(math.pi * t)
        lng = -96.7970 + (-104.9903 + 96.7970) * t + offset * 0.8 * math.sin(math.pi * t)
        points.append(RoutePoint(lat=lat, lng=lng))
    return encode_polyline(points)


def fake_weather(points, start, end, variables=None):
    """Weather depends on longitude so one corridor is windy and one is calm."""
    departure = datetime.now(UTC) + timedelta(hours=6)
    times = [departure - timedelta(hours=1) + timedelta(hours=index) for index in range(30)]
    result = {}
    for lat, lng in points:
        windy = lat > 35.5 and lng > -100.0
        wind = 38.0 if windy else 8.0
        result[coord_key(lat, lng)] = {
            "times": times,
            "wind_mph": [wind] * len(times),
            "rain_in": [0.0] * len(times),
            "snow_in": [0.0] * len(times),
            "temp_f": [70.0] * len(times),
            "weather_code": [0.0] * len(times),
            "visibility_ft": [52800.0] * len(times),
        }
    return result


def fake_resolve(value):
    if isinstance(value, dict):
        return {
            "label": value.get("label", ""),
            "primary": value.get("primary", ""),
            "secondary": "",
            "lat": value["lat"],
            "lng": value["lng"],
            "city": value.get("city", ""),
            "state": value.get("state", ""),
            "country": "US",
            "place_id": "",
        }
    if "Dallas" in str(value):
        return {
            "label": "Dallas, TX, USA",
            "primary": "Dallas",
            "secondary": "Texas, United States",
            "lat": 32.7767,
            "lng": -96.797,
            "city": "Dallas",
            "state": "TX",
            "country": "US",
            "place_id": "dallas",
        }
    return {
        "label": "Denver, CO, USA",
        "primary": "Denver",
        "secondary": "Colorado, United States",
        "lat": 39.7392,
        "lng": -104.9903,
        "city": "Denver",
        "state": "CO",
        "country": "US",
        "place_id": "denver",
    }


class RiskSummaryTests(SimpleTestCase):
    def checkpoint(self, mile, level):
        return {"mile": mile, "risk": {"level": level}}

    def test_trapezoid_weights_cover_distance(self):
        checkpoints = [
            self.checkpoint(0, "low"),
            self.checkpoint(50, "severe"),
            self.checkpoint(100, "low"),
        ]
        summary = _summarise_risk(checkpoints, 100)
        self.assertAlmostEqual(summary["severe_miles"], 50.0, delta=0.1)
        self.assertAlmostEqual(summary["low_miles"], 50.0, delta=0.1)
        self.assertAlmostEqual(summary["avg_risk"], 2.5, delta=0.01)
        self.assertEqual(summary["level"], "severe")

    def test_no_travel_counts_as_severe_for_ranking(self):
        checkpoints = [
            self.checkpoint(0, "low"),
            self.checkpoint(40, "no_travel"),
            self.checkpoint(80, "high"),
        ]
        summary = _summarise_risk(checkpoints, 80)
        self.assertGreater(summary["severe_miles"], 0)
        self.assertEqual(summary["no_travel_miles"], 40.0)
        self.assertEqual(summary["level"], "no_travel")

    def test_single_checkpoint(self):
        summary = _summarise_risk([self.checkpoint(0, "moderate")], 10)
        self.assertEqual(summary["level"], "moderate")
        self.assertAlmostEqual(summary["avg_risk"], 2.0)


class RecommendationOrderTests(SimpleTestCase):
    def route(self, route_id, severe, high, avg, duration):
        option = RouteOption(
            polyline=f"polyline-{route_id}",
            distance_meters=100 * 1609.344,
            duration_seconds=duration,
            static_duration_seconds=duration,
        )
        return PlannedRoute(
            option=option,
            route_id=route_id,
            checkpoints=[],
            risk={
                "severe_miles": severe,
                "high_miles": high,
                "risk_score_avg": avg,
                "avg_risk": avg,
            },
        )

    def test_lexicographic_priority(self):
        routes = [
            self.route("a", severe=30, high=0, avg=1.1, duration=1000),
            self.route("b", severe=0, high=40, avg=1.2, duration=900),
            self.route("c", severe=0, high=0, avg=1.3, duration=1200),
            self.route("d", severe=0, high=0, avg=1.3, duration=800),
        ]
        ordered = [route.route_id for route in sorted(routes, key=_route_sort_key)]
        self.assertEqual(ordered, ["d", "c", "b", "a"])

    def test_severe_miles_beats_travel_time(self):
        fast_but_dangerous = self.route("fast", severe=25, high=0, avg=1.0, duration=100)
        slow_but_safe = self.route("safe", severe=0, high=0, avg=1.5, duration=999)
        ordered = sorted([fast_but_dangerous, slow_but_safe], key=_route_sort_key)
        self.assertEqual(ordered[0].route_id, "safe")


class PlanBuildTests(SimpleTestCase):
    def setUp(self):
        self.departure = datetime.now(UTC) + timedelta(hours=6)
        self.options = [
            RouteOption(
                polyline=synthetic_route(offset=1.0),
                distance_meters=800 * 1609.344,
                duration_seconds=36000,
                static_duration_seconds=35000,
                description="Windy corridor",
            ),
            RouteOption(
                polyline=synthetic_route(offset=-1.0),
                distance_meters=810 * 1609.344,
                duration_seconds=38000,
                static_duration_seconds=37000,
                description="Calm corridor",
            ),
        ]

    def build(self):
        payload = {
            "origin": "Dallas, TX",
            "destination": "Denver, CO",
            "departure_time": self.departure.isoformat(),
            "load_lb": 30000,
            "sample_interval_miles": 50,
        }
        with (
            patch.object(planner, "fetch_routes", return_value=self.options),
            patch.object(planner, "fetch_weather", side_effect=fake_weather),
            patch.object(planner, "resolve_location", side_effect=fake_resolve),
        ):
            return build_plan(payload)

    def test_builds_routes_and_ranks_safe_route_first(self):
        plan = self.build()
        self.assertEqual(len(plan["routes"]), 2)
        self.assertEqual(plan["routes"][0]["name"], "Route A")
        self.assertEqual(plan["routes"][1]["name"], "Route B")
        self.assertTrue(plan["routes"][0]["is_recommended"])
        self.assertEqual(plan["routes"][0]["description"], "Calm corridor")
        self.assertEqual(plan["routes"][0]["risk"]["high_miles"], 0.0)
        self.assertGreater(plan["routes"][1]["risk"]["high_miles"], 0.0)
        self.assertEqual(plan["recommendation"]["ranked_route_ids"][0], plan["routes"][0]["id"])

    def test_route_and_checkpoint_payload(self):
        plan = self.build()
        route = plan["routes"][0]
        self.assertGreater(len(route["checkpoints"]), 5)
        checkpoint = route["checkpoints"][1]
        self.assertIn("risk", checkpoint)
        self.assertIn("weather", checkpoint)
        self.assertIn("eta", checkpoint)
        self.assertAlmostEqual(route["distance_miles"], 810, delta=2)
        miles = [checkpoint["mile"] for checkpoint in route["checkpoints"]]
        self.assertTrue(
            all(round(b - a) == 50 for a, b in zip(miles[:-1], miles[1:-1], strict=False))
        )
        self.assertEqual(plan["sample_interval_miles"], 50)
        self.assertEqual(plan["meta"]["weather_points"], sum(len(r["checkpoints"]) for r in plan["routes"]))
        self.assertEqual(plan["load_lb"], 30000)
        self.assertIn("fewest severe-weather miles", " ".join(plan["recommendation"]["criteria"]).lower())

    def test_invalid_sample_interval(self):
        from routing.services.planner import PlanValidationError

        with self.assertRaises(PlanValidationError):
            build_plan(
                {
                    "origin": "Dallas, TX",
                    "destination": "Denver, CO",
                    "departure_time": self.departure.isoformat(),
                    "load_lb": 44000,
                    "sample_interval_miles": 30,
                }
            )

    def test_invalid_load(self):
        from routing.services.planner import PlanValidationError

        with self.assertRaises(PlanValidationError):
            build_plan(
                {
                    "origin": "Dallas, TX",
                    "destination": "Denver, CO",
                    "departure_time": self.departure.isoformat(),
                    "load_lb": -1,
                    "sample_interval_miles": 25,
                }
            )
