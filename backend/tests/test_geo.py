from __future__ import annotations

import math
import unittest

from app.geo import haversine_m, utm_forward, generate_synthetic_points


class GeoTests(unittest.TestCase):
    def test_haversine_known_behaviour(self) -> None:
        self.assertEqual(haversine_m(24.86, 67.0, 24.86, 67.0), 0.0)
        a_to_b = haversine_m(24.86, 67.0, 24.87, 67.0)
        b_to_a = haversine_m(24.87, 67.0, 24.86, 67.0)
        self.assertAlmostEqual(a_to_b, b_to_a, places=6)
        self.assertTrue(1_000 < a_to_b < 1_200)

    def test_utm_projection(self) -> None:
        easting, northing = utm_forward(24.8607, 67.0011, zone=42)
        self.assertTrue(math.isfinite(easting))
        self.assertTrue(math.isfinite(northing))
        self.assertTrue(200_000 < easting < 400_000)
        self.assertTrue(2_700_000 < northing < 2_800_000)

    def test_synthetic_dataset_is_deterministic(self) -> None:
        first = generate_synthetic_points(50, seed=7, clustered=True, bounds=None)
        second = generate_synthetic_points(50, seed=7, clustered=True, bounds=None)
        self.assertEqual([(p.lat, p.lng) for p in first], [(p.lat, p.lng) for p in second])
        self.assertEqual(len({p.id for p in first}), 50)


if __name__ == "__main__":
    unittest.main()
