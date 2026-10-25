from django.test import SimpleTestCase

from routing.services.polyline import (
    RoutePoint,
    cumulative_distances,
    decode_polyline,
    haversine_miles,
    interpolate,
    sample_route,
)


class PolylineDecodeTests(SimpleTestCase):
    def test_decodes_google_example(self):
        # Official encoded polyline example from Google's documentation.
        points = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
        self.assertEqual(len(points), 3)
        self.assertAlmostEqual(points[0].lat, 38.5, places=4)
        self.assertAlmostEqual(points[0].lng, -120.2, places=4)
        self.assertAlmostEqual(points[1].lat, 40.7, places=4)
        self.assertAlmostEqual(points[1].lng, -120.95, places=4)
        self.assertAlmostEqual(points[2].lat, 43.252, places=4)
        self.assertAlmostEqual(points[2].lng, -126.453, places=4)

    def test_empty_polyline(self):
        self.assertEqual(decode_polyline(""), [])


class DistanceTests(SimpleTestCase):
    def test_haversine_one_degree_latitude(self):
        distance = haversine_miles((0, 0), (1, 0))
        self.assertAlmostEqual(distance, 69.09, delta=0.2)

    def test_cumulative_distances(self):
        points = [RoutePoint(0, 0), RoutePoint(1, 0), RoutePoint(2, 0)]
        cumulative = cumulative_distances(points)
        self.assertEqual(cumulative[0], 0)
        self.assertAlmostEqual(cumulative[1], 69.09, delta=0.2)
        self.assertAlmostEqual(cumulative[2], 138.18, delta=0.4)

    def test_interpolates_between_vertices(self):
        points = [RoutePoint(0, 0), RoutePoint(0, 2)]
        cumulative = cumulative_distances(points)
        midpoint = interpolate(points, cumulative, cumulative[-1] / 2)
        self.assertAlmostEqual(midpoint.lat, 0, places=6)
        self.assertAlmostEqual(midpoint.lng, 1, places=6)

    def test_interpolation_clamps_to_endpoints(self):
        points = [RoutePoint(1, 2), RoutePoint(3, 4)]
        cumulative = cumulative_distances(points)
        self.assertEqual(interpolate(points, cumulative, -5), points[0])
        self.assertEqual(interpolate(points, cumulative, 999), points[1])


class SamplingTests(SimpleTestCase):
    def test_samples_fixed_interval_and_destination(self):
        points = [RoutePoint(0, 0), RoutePoint(0, 1)]  # ~69.09 miles
        samples, total = sample_route(points, 10)
        self.assertAlmostEqual(total, 69.09, delta=0.3)
        self.assertEqual(samples[0].mile, 0)
        self.assertAlmostEqual(samples[0].fraction, 0)
        self.assertEqual(samples[-1].mile, total)
        self.assertAlmostEqual(samples[-1].fraction, 1)
        # 0, 10, 20, 30, 40, 50, 60, 69.09
        self.assertEqual(len(samples), 8)
        for previous, current in zip(samples, samples[1:], strict=False):
            self.assertGreater(current.mile, previous.mile)

    def test_short_route_merges_tiny_stub(self):
        # 12 miles at a 10 mile interval should produce start + destination,
        # not a 10 mile checkpoint followed by a 2 mile stub.
        points = [RoutePoint(0, 0), RoutePoint(0, 12 / 69.09)]
        samples, total = sample_route(points, 10)
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[-1].mile, total)

    def test_sample_count_for_long_route(self):
        points = [RoutePoint(0, 0), RoutePoint(0, 10 / 69.09)]
        samples, _ = sample_route(points, 10)
        self.assertEqual([round(s.mile) for s in samples], [0, 10])

    def test_zero_length_route_is_rejected(self):
        with self.assertRaises(ValueError):
            sample_route([RoutePoint(0, 0), RoutePoint(0, 0)], 10)
