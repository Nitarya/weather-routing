"""Simple HTTP Basic Auth gate for public deployments."""

from __future__ import annotations

import base64
import binascii
import secrets

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class BasicAuthMiddleware:
    """Protect the app and API with one shared username/password.

    The health endpoint stays public so a hosting platform can check liveness
    without exposing any billable Google API path.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == "/api/health/":
            return self.get_response(request)

        if not settings.APP_PASSWORD:
            if settings.DEBUG:
                return self.get_response(request)
            return HttpResponse(
                "APP_PASSWORD is not configured. Set it before exposing this app.",
                status=503,
                content_type="text/plain",
            )

        header = request.headers.get("Authorization", "")
        if not header[:6].lower() == "basic ":
            return self._challenge()

        try:
            decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return self._challenge()

        user_ok = secrets.compare_digest(username, settings.APP_USERNAME)
        password_ok = secrets.compare_digest(password, settings.APP_PASSWORD)
        if user_ok and password_ok:
            return self.get_response(request)

        return self._challenge()

    @staticmethod
    def _challenge() -> HttpResponse:
        response = HttpResponse("Authentication required.", status=401, content_type="text/plain")
        response["WWW-Authenticate"] = 'Basic realm="Route Weather", charset="UTF-8"'
        return response
