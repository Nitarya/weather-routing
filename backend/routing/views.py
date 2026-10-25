from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services.geocoding import LocationError
from .services.geocoding import reverse_geocode as lookup_area
from .services.heatmap import HeatmapError, build_heatmap
from .services.planner import PlannerError, PlanValidationError, build_plan

logger = logging.getLogger(__name__)


def _error(message: str, status: int, code: str) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _parse_body(request: HttpRequest) -> dict[str, Any]:
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PlanValidationError("Request body must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise PlanValidationError("Request body must be a JSON object.")
    return payload


def index(request: HttpRequest) -> HttpResponse:
    """Serve the compiled React app (Vite manifest) or a dev helper page."""
    manifest_path = settings.BASE_DIR / "static" / "frontend" / ".vite" / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            entry = manifest.get("index.html") or next(iter(manifest.values()))
            context = {
                "styles": [static(f"frontend/{path}") for path in entry.get("css", [])],
                "scripts": [static(f"frontend/{entry['file']}")],
            }
            return render(request, "app.html", context)
        except (json.JSONDecodeError, KeyError, StopIteration) as exc:
            logger.error("Could not read Vite manifest: %s", exc)

    return render(request, "dev.html", {"vite_url": "http://localhost:5173"})


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "status": "ok",
            "google_key_configured": bool(settings.GOOGLE_MAPS_API_KEY),
            "frontend_built": (
                settings.BASE_DIR / "static" / "frontend" / ".vite" / "manifest.json"
            ).exists(),
        }
    )


@require_GET
def config(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "map_api_key": settings.GOOGLE_MAPS_API_KEY,
            "sample_intervals": list(settings.SAMPLE_INTERVALS),
            "forecast_hours": settings.FORECAST_HOURS,
        }
    )


@require_GET
def reverse_geocode(request: HttpRequest) -> JsonResponse:
    try:
        lat = float(request.GET.get("lat", ""))
        lng = float(request.GET.get("lng", ""))
    except (TypeError, ValueError):
        return _error("lat and lng are required.", 400, "invalid_request")
    try:
        return JsonResponse({"area": lookup_area(lat, lng)})
    except LocationError as exc:
        logger.warning("Reverse geocode failed: %s", exc)
        return _error(str(exc), 502, "geocoding_error")


@csrf_exempt
@require_POST
def plan(request: HttpRequest) -> JsonResponse:
    try:
        return JsonResponse(build_plan(_parse_body(request)))
    except PlanValidationError as exc:
        return _error(str(exc), 400, "invalid_request")
    except PlannerError as exc:
        logger.warning("Plan failed: %s", exc)
        return _error(str(exc), 502, "planning_error")
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected planning error")
        return _error("Something went wrong while planning this route.", 500, "internal_error")


@csrf_exempt
@require_POST
def heatmap(request: HttpRequest) -> JsonResponse:
    try:
        return JsonResponse(build_heatmap(_parse_body(request)))
    except PlanValidationError as exc:
        return _error(str(exc), 400, "invalid_request")
    except HeatmapError as exc:
        logger.warning("Heatmap failed: %s", exc)
        return _error(str(exc), 502, "heatmap_error")
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected heatmap error")
        return _error("Something went wrong while building the heatmap.", 500, "internal_error")
