from __future__ import annotations

import unittest

from app.engine import engine, ENGINE_MODE


class EngineTests(unittest.TestCase):
    def test_closest_pair_algorithms_agree(self) -> None:
        points = [(0, 0), (1, 0.1), (2, 0), (3, 0.1)]
        brute = engine.closest_pair(points, "brute_force")
        divide = engine.closest_pair(points, "divide_conquer")
        self.assertAlmostEqual(brute.distance, divide.distance, places=9)
        self.assertEqual(
            {brute.index_a, brute.index_b}, {divide.index_a, divide.index_b}
        )
        self.assertEqual(ENGINE_MODE, "native-cpp17")

    def test_tsp_algorithms(self) -> None:
        matrix = [
            [0, 2, 9, 4],
            [2, 0, 6, 3],
            [9, 6, 0, 5],
            [4, 3, 5, 0],
        ]
        exact = engine.tsp(matrix, 0, "exact")
        nearest = engine.tsp(matrix, 0, "nearest_neighbor")
        improved = engine.tsp(matrix, 0, "two_opt")
        self.assertAlmostEqual(exact.cost, 17.0, places=9)
        self.assertGreaterEqual(nearest.cost, exact.cost)
        self.assertGreaterEqual(improved.cost, exact.cost)
        self.assertLessEqual(improved.cost, nearest.cost)
        for result in (exact, nearest, improved):
            self.assertEqual(result.route[0], 0)
            self.assertEqual(sorted(result.route), [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
