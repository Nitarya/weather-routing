from __future__ import annotations

import base64

from django.test import Client, SimpleTestCase, override_settings


def basic(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


@override_settings(APP_USERNAME="route", APP_PASSWORD="secret", DEBUG=False)
class BasicAuthTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_app_requires_authentication(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic", response["WWW-Authenticate"])

    def test_health_is_public(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)

    def test_correct_credentials_allow_api(self):
        response = self.client.get("/api/config/", HTTP_AUTHORIZATION=basic("route", "secret"))
        self.assertEqual(response.status_code, 200)

    def test_wrong_password_is_rejected(self):
        response = self.client.get(
            "/api/config/", HTTP_AUTHORIZATION=basic("route", "wrong")
        )
        self.assertEqual(response.status_code, 401)

    def test_malformed_header_is_rejected(self):
        response = self.client.get("/api/config/", HTTP_AUTHORIZATION="Basic not-base64!")
        self.assertEqual(response.status_code, 401)

    @override_settings(APP_PASSWORD="", DEBUG=False)
    def test_production_does_not_serve_without_a_password(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 503)
