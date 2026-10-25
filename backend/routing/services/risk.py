"""Weather + load risk model.

The thresholds come directly from the assessment brief.  Boundary values are
treated as the *lower* bound of the next band (for example 0.25 in/hr of rain is
High, not Moderate).  The load rules can only upgrade a risk level, never
downgrade it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LOW = "low"
MODERATE = "moderate"
HIGH = "high"
SEVERE = "severe"
NO_TRAVEL = "no_travel"

LEVELS = (LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL)
LEVEL_SCORE = {LOW: 1, MODERATE: 2, HIGH: 3, SEVERE: 4, NO_TRAVEL: 5}
LEVEL_LABEL = {
    LOW: "Low",
    MODERATE: "Moderate",
    HIGH: "High",
    SEVERE: "Severe",
    NO_TRAVEL: "No Travel",
}
LEVEL_RANK = {level: index for index, level in enumerate(LEVELS)}

# UI colours are duplicated in the frontend theme; keeping them in the API makes
# it easy to render legends from a single source of truth.
LEVEL_COLOR = {
    LOW: "#2dd4bf",
    MODERATE: "#facc15",
    HIGH: "#fb923c",
    SEVERE: "#f43f5e",
    NO_TRAVEL: "#a855f7",
}


@dataclass(frozen=True)
class RiskAssessment:
    level: str
    score: int
    label: str
    reasons: list[str] = field(default_factory=list)
    factors: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "score": self.score,
            "label": self.label,
            "reasons": self.reasons,
            "factors": self.factors,
            "color": LEVEL_COLOR[self.level],
        }


def _level_for_thresholds(
    value: float,
    *,
    moderate: float,
    high: float,
    severe: float,
    no_travel: float,
) -> str:
    if value >= no_travel:
        return NO_TRAVEL
    if value >= severe:
        return SEVERE
    if value >= high:
        return HIGH
    if value >= moderate:
        return MODERATE
    return LOW


def classify_wind(mph: float) -> str:
    return _level_for_thresholds(mph, moderate=25, high=35, severe=45, no_travel=55)


def classify_rain(inches_per_hour: float) -> str:
    return _level_for_thresholds(
        inches_per_hour, moderate=0.10, high=0.25, severe=0.50, no_travel=1.000001
    )


def classify_snow(inches_per_hour: float) -> str:
    return _level_for_thresholds(
        inches_per_hour, moderate=0.5, high=1.0, severe=2.0, no_travel=3.000001
    )


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def assess_weather(
    *,
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_lb: float,
) -> RiskAssessment:
    """Classify one checkpoint and apply the load-dependent overrides."""

    wind_mph = max(0.0, float(wind_mph or 0.0))
    rain_in_hr = max(0.0, float(rain_in_hr or 0.0))
    snow_in_hr = max(0.0, float(snow_in_hr or 0.0))
    load_lb = max(0.0, float(load_lb or 0.0))

    factor_levels = {
        "wind": classify_wind(wind_mph),
        "rain": classify_rain(rain_in_hr),
        "snow": classify_snow(snow_in_hr),
    }
    base_level = max(factor_levels.values(), key=lambda level: LEVEL_RANK[level])
    level = base_level
    reasons: list[str] = []

    if factor_levels["wind"] != LOW:
        reasons.append(f"Wind {_fmt(wind_mph)} mph ({LEVEL_LABEL[factor_levels['wind']]})")
    if factor_levels["rain"] != LOW:
        reasons.append(
            f"Rain {_fmt(rain_in_hr, 2)} in/hr ({LEVEL_LABEL[factor_levels['rain']]})"
        )
    if factor_levels["snow"] != LOW:
        reasons.append(
            f"Snow {_fmt(snow_in_hr, 2)} in/hr ({LEVEL_LABEL[factor_levels['snow']]})"
        )

    # Load rules from the brief.
    if wind_mph >= 55:
        level = NO_TRAVEL
        reasons.append("Wind ≥ 55 mph — no travel for any load")
    elif wind_mph >= 45 and load_lb > 30_000:
        level = NO_TRAVEL
        reasons.append(
            f"Wind {_fmt(wind_mph)} mph + {load_lb:,.0f} lb load (> 30,000 lb) — no travel"
        )
    elif wind_mph >= 35 and load_lb > 40_000:
        if LEVEL_RANK[level] < LEVEL_RANK[SEVERE]:
            level = SEVERE
        reasons.append(
            f"Wind {_fmt(wind_mph)} mph + {load_lb:,.0f} lb load (> 40,000 lb) — severe"
        )

    if not reasons:
        reasons.append("Weather within low-risk thresholds for this load")

    return RiskAssessment(
        level=level,
        score=LEVEL_SCORE[level],
        label=LEVEL_LABEL[level],
        reasons=reasons,
        factors=factor_levels,
    )


def risk_meta() -> dict[str, Any]:
    """Threshold metadata used by the API/UI legend."""

    return {
        "levels": [
            {
                "level": level,
                "label": LEVEL_LABEL[level],
                "score": LEVEL_SCORE[level],
                "color": LEVEL_COLOR[level],
            }
            for level in LEVELS
        ],
        "thresholds": {
            "wind_mph": {"moderate": 25, "high": 35, "severe": 45, "no_travel": 55},
            "rain_in_hr": {"moderate": 0.10, "high": 0.25, "severe": 0.50, "no_travel": 1.00},
            "snow_in_hr": {"moderate": 0.5, "high": 1.0, "severe": 2.0, "no_travel": 3.0},
            "load_rules": [
                "≥ 55 mph → No Travel for any load",
                "45–54 mph + > 30,000 lb → No Travel",
                "35–44 mph + > 40,000 lb → Severe",
            ],
        },
    }
