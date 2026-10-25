from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from routing.services import weather


def hour_entry(
    start: datetime,
    *,
    wind: float = 10.0,
    rain: float = 0.1,
    snow_liquid: float = 0.02,
    temp: float = 70.0,
    visibility: float = 10.0,
    condition_type: str = "RAIN",
    description: str = "Rain",
) -> dict:
    return {
        "interval": {
            "startTime": start.isoformat().replace("+00:00", "Z"),
            "endTime": (start + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        },
        "weatherCondition": {
            "type": condition_type,
            "description": {"text": description, "languageCode": "en"},
        },
        "temperature": {"unit": "FAHRENHEIT", "degrees": temp},
        "precipitation": {
            "qpf": {"unit": "INCHES", "quantity": rain},
            "snowQpf": {"unit": "INCHES", "quantity": snow_liquid},
        },
        "wind": {"speed": {"unit": "MILES_PER_HOUR", "value": wind}},
        "visibility": {"unit": "MILES", "distance": visibility},
    }


def response(payload: dict) -> Mock:
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = payload
    return mock


class GoogleWeatherTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    @patch("routing.services.weather._get")
    def test_normalises_imperial_google_payload(self, get_mock):
        get_mock.return_value = response(
            {"forecastHours": [hour_entry(self.now + timedelta(hours=1))]}
        )
        series = weather.fetch_weather(
            [(32.7767, -96.797)],
            self.now,
            self.now + timedelta(hours=3),
        )
        point = series[weather.coord_key(32.7767, -96.797)]
        self.assertEqual(point["wind_mph"][0], 10.0)
        self.assertEqual(point["rain_in"][0], 0.1)
        # Google gives liquid-water equivalent; the risk model uses 10:1 depth.
        self.assertAlmostEqual(point["snow_in"][0], 0.2, places=4)
        self.assertEqual(point["temp_f"][0], 70.0)
        self.assertEqual(point["visibility_ft"][0], 52800.0)
        self.assertEqual(point["condition_keys"][0], "rain")

        sampled = weather.weather_at(point, self.now + timedelta(hours=1))
        self.assertIsNotNone(sampled)
        assert sampled is not None
        self.assertEqual(sampled["rain_in_hr"], 0.1)
        self.assertEqual(sampled["snow_in_hr"], 0.2)
        self.assertEqual(sampled["condition"], "Rain")

    @patch("routing.services.weather._get")
    def test_paginates_until_window_is_covered(self, get_mock):
        page_one = [hour_entry(self.now + timedelta(hours=offset)) for offset in range(24)]
        page_two = [
            hour_entry(self.now + timedelta(hours=offset)) for offset in range(24, 32)
        ]
        get_mock.side_effect = [
            response({"forecastHours": page_one, "nextPageToken": "next"}),
            response({"forecastHours": page_two, "nextPageToken": None}),
        ]
        series = weather.fetch_weather(
            [(32.7767, -96.797)],
            self.now,
            self.now + timedelta(hours=31),
        )
        point = series[weather.coord_key(32.7767, -96.797)]
        self.assertEqual(len(point["times"]), 32)
        self.assertEqual(get_mock.call_count, 2)
        second_params = get_mock.call_args_list[1].args[1]
        self.assertEqual(second_params["pageToken"], "next")
        self.assertEqual(second_params["unitsSystem"], "IMPERIAL")

    @patch("routing.services.weather._get")
    def test_rejects_weather_api_permission_errors(self, get_mock):
        denied = Mock()
        denied.status_code = 403
        denied.json.return_value = {"error": {"message": "Weather API is not enabled"}}
        get_mock.return_value = denied
        with self.assertRaises(weather.WeatherError):
            weather.fetch_weather(
                [(32.7767, -96.797)],
                self.now,
                self.now + timedelta(hours=2),
            )

    def test_converts_metric_units_if_returned(self):
        metric_entry = hour_entry(self.now, wind=16.0)
        metric_entry["wind"]["speed"]["unit"] = "KILOMETERS_PER_HOUR"
        metric_entry["temperature"]["unit"] = "CELSIUS"
        metric_entry["temperature"]["degrees"] = 20.0
        metric_entry["visibility"]["unit"] = "KILOMETERS"
        metric_entry["precipitation"]["qpf"]["unit"] = "MILLIMETERS"
        metric_entry["precipitation"]["qpf"]["quantity"] = 25.4
        series = weather._normalise([metric_entry])
        self.assertAlmostEqual(series["wind_mph"][0], 9.94, places=1)
        self.assertAlmostEqual(series["temp_f"][0], 68.0, places=1)
        self.assertAlmostEqual(series["rain_in"][0], 1.0, places=2)
        self.assertAlmostEqual(series["visibility_ft"][0], 32808.4, delta=2)
