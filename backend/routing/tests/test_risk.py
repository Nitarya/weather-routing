from django.test import SimpleTestCase

from routing.services.risk import (
    HIGH,
    LOW,
    MODERATE,
    NO_TRAVEL,
    SEVERE,
    assess_weather,
    classify_rain,
    classify_snow,
    classify_wind,
)


class WindThresholdTests(SimpleTestCase):
    def test_wind_bands(self):
        cases = [
            (0, LOW),
            (24.9, LOW),
            (25, MODERATE),
            (34.9, MODERATE),
            (35, HIGH),
            (44.9, HIGH),
            (45, SEVERE),
            (54.9, SEVERE),
            (55, NO_TRAVEL),
            (80, NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_wind(value), expected)


class RainThresholdTests(SimpleTestCase):
    def test_rain_bands(self):
        cases = [
            (0.0, LOW),
            (0.099, LOW),
            (0.10, MODERATE),
            (0.249, MODERATE),
            (0.25, HIGH),
            (0.499, HIGH),
            (0.50, SEVERE),
            (1.00, SEVERE),
            (1.001, NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_rain(value), expected)


class SnowThresholdTests(SimpleTestCase):
    def test_snow_bands(self):
        cases = [
            (0.0, LOW),
            (0.49, LOW),
            (0.5, MODERATE),
            (0.99, MODERATE),
            (1.0, HIGH),
            (1.99, HIGH),
            (2.0, SEVERE),
            (3.0, SEVERE),
            (3.001, NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_snow(value), expected)


class LoadRuleTests(SimpleTestCase):
    def assess(self, wind, load, rain=0.0, snow=0.0):
        return assess_weather(wind_mph=wind, rain_in_hr=rain, snow_in_hr=snow, load_lb=load)

    def test_any_load_at_55_mph_is_no_travel(self):
        self.assertEqual(self.assess(55, 0).level, NO_TRAVEL)
        self.assertEqual(self.assess(70, 80_000).level, NO_TRAVEL)

    def test_heavy_load_above_30k_turns_45_mph_into_no_travel(self):
        self.assertEqual(self.assess(50, 30_000).level, SEVERE)
        self.assertEqual(self.assess(50, 30_001).level, NO_TRAVEL)
        self.assertEqual(self.assess(45, 44_000).level, NO_TRAVEL)
        self.assertEqual(self.assess(54, 60_000).level, NO_TRAVEL)

    def test_very_heavy_load_above_40k_turns_35_mph_into_severe(self):
        self.assertEqual(self.assess(40, 40_000).level, HIGH)
        self.assertEqual(self.assess(40, 40_001).level, SEVERE)
        self.assertEqual(self.assess(35, 44_000).level, SEVERE)
        self.assertEqual(self.assess(34.9, 44_000).level, MODERATE)

    def test_load_rules_do_not_downgrade_other_hazards(self):
        result = self.assess(10, 60_000, rain=0.6)
        self.assertEqual(result.level, SEVERE)
        self.assertIn("Rain", " ".join(result.reasons))

    def test_no_travel_beats_severe(self):
        result = self.assess(55, 60_000, rain=0.6, snow=2.5)
        self.assertEqual(result.level, NO_TRAVEL)
        self.assertEqual(result.score, 5)

    def test_base_level_uses_worst_factor(self):
        result = self.assess(10, 20_000, snow=1.2)
        self.assertEqual(result.level, HIGH)
        self.assertEqual(result.factors["snow"], HIGH)

    def test_reasons_explain_a_low_checkpoint(self):
        result = self.assess(5, 20_000)
        self.assertEqual(result.level, LOW)
        self.assertTrue(result.reasons)
