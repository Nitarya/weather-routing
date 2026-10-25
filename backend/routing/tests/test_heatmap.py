from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase

from routing.services.heatmap import build_heatmap
from routing.tests.test_planner import encode_polyline, fake_weather, synthetic_route


class HeatmapTests(SimpleTestCase):
    def setUp(self):
        self.departure = datetime.now(UTC) + timedelta(hours=3)
        self.polyline = synthetic_route(offset=0.4)

    def test_builds_full_48_hour_matrix(self):
        with patch(
            "routing.services.heatmap.fetch_weather", side_effect=fake_weather
        ) as weather_mock:
            heatmap = build_heatmap(
                {
                    "polyline": self.polyline,
                    "departure_time": self.departure.isoformat(),
                    "load_lb": 30000,
                    "hours": 48,
                }
            )
        self.assertEqual(len(heatmap["hours"]), 49)
        self.assertEqual(len(heatmap["summary"]), 49)
        self.assertGreater(heatmap["cell_count"], 0)
        self.assertTrue(all(len(cell["risks"]) == 49 for cell in heatmap["cells"]))
        self.assertTrue(all(item["hour"] == index for index, item in enumerate(heatmap["summary"])))
        self.assertGreater(heatmap["spacing_miles"], 0)
        weather_mock.assert_called_once()

    def test_single_polyline_is_supported(self):
        with patch("routing.services.heatmap.fetch_weather", side_effect=fake_weather):
            heatmap = build_heatmap(
                {
                    "polyline": self.polyline,
                    "departure_time": self.departure.isoformat(),
                    "load_lb": 26000,
                    "hours": 12,
                }
            )
        self.assertEqual(len(heatmap["hours"]), 13)

    def test_rejects_missing_geometry(self):
        from routing.services.planner import PlanValidationError

        with self.assertRaises(PlanValidationError):
            build_heatmap(
                {
                    "departure_time": self.departure.isoformat(),
                    "load_lb": 26000,
                }
            )

    def test_rejects_bad_load(self):
        from routing.services.planner import PlanValidationError

        with self.assertRaises(PlanValidationError):
            build_heatmap(
                {
                    "polyline": self.polyline,
                    "departure_time": self.departure.isoformat(),
                    "load_lb": -5,
                }
            )


class PolylineEncoderTestHelper(SimpleTestCase):
    def test_test_encoder_round_trips(self):
        from routing.services.polyline import decode_polyline

        encoded = encode_polyline(
            [
                type("P", (), {"lat": 32.7767, "lng": -96.797})(),
                type("P", (), {"lat": 39.7392, "lng": -104.9903})(),
            ]
        )
        points = decode_polyline(encoded)
        self.assertAlmostEqual(points[0].lat, 32.7767, places=4)
        self.assertAlmostEqual(points[1].lng, -104.9903, places=4)
