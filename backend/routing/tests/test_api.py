from __future__ import annotations

import base64
import json
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from routing.services.planner import PlannerError, PlanValidationError

AUTH = "Basic " + base64.b64encode(b"route:test-password").decode()


def authed_client() -> Client:
    return Client(HTTP_AUTHORIZATION=AUTH)

@override_settings(APP_USERNAME="route", APP_PASSWORD="test-password")
class ConfigEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = authed_client()

    def test_config_contract(self):
        response = self.client.get("/api/config/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("map_api_key", payload)
        self.assertEqual(payload["sample_intervals"], [10, 25, 50])
        self.assertEqual(payload["forecast_hours"], 48)

    def test_health(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_index_serves_spa_or_build_instructions(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            b'id="root"' in response.content
            or b"frontend needs a build" in response.content
        )


@override_settings(APP_USERNAME="route", APP_PASSWORD="test-password")
class ReverseGeocodeEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = authed_client()

    @override_settings(APP_USERNAME="route", APP_PASSWORD="test-password")
    @patch("routing.views.lookup_area", return_value="Green River, WY")
    def test_reverse_geocode_returns_area(self, lookup_mock):
        response = self.client.get("/api/reverse-geocode/?lat=41.5&lng=-109.4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["area"], "Green River, WY")
        lookup_mock.assert_called_once_with(41.5, -109.4)

    @override_settings(APP_USERNAME="route", APP_PASSWORD="test-password")
    def test_reverse_geocode_requires_coordinates(self):
        response = self.client.get("/api/reverse-geocode/")
        self.assertEqual(response.status_code, 400)


@override_settings(APP_USERNAME="route", APP_PASSWORD="test-password")
class PlanEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = authed_client()

    @patch("routing.views.build_plan")
    def test_plan_success(self, build_mock):
        build_mock.return_value = {"routes": []}
        response = self.client.post(
            "/api/plan/",
            data=json.dumps(
                {
                    "origin": "Dallas, TX",
                    "destination": "Denver, CO",
                    "departure_time": "2030-01-01T10:00:00Z",
                    "load_lb": 44000,
                    "sample_interval_miles": 25,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"routes": []})

    def test_plan_rejects_malformed_json(self):
        response = self.client.post(
            "/api/plan/", data="{invalid", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")

    @patch("routing.views.build_plan", side_effect=PlanValidationError("bad input"))
    def test_plan_returns_400_for_validation(self, _mock):
        response = self.client.post(
            "/api/plan/", data=json.dumps({}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["message"], "bad input")

    @patch("routing.views.build_plan", side_effect=PlannerError("weather down"))
    def test_plan_returns_502_for_upstream_failure(self, _mock):
        response = self.client.post(
            "/api/plan/", data=json.dumps({}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "planning_error")

    def test_plan_requires_post(self):
        response = self.client.get("/api/plan/")
        self.assertEqual(response.status_code, 405)


@override_settings(APP_USERNAME="route", APP_PASSWORD="test-password")
class HeatmapEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = authed_client()

    @patch("routing.views.build_heatmap")
    def test_heatmap_success(self, build_mock):
        build_mock.return_value = {"hours": [], "cells": []}
        response = self.client.post(
            "/api/heatmap/",
            data=json.dumps(
                {
                    "polyline": "abc",
                    "departure_time": "2030-01-01T10:00:00Z",
                    "load_lb": 44000,
                    "hours": 48,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_heatmap_requires_post(self):
        response = self.client.get("/api/heatmap/")
        self.assertEqual(response.status_code, 405)
