from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("engine", response.json())

    def test_synthetic_dataset(self) -> None:
        response = self.client.post(
            "/api/datasets/synthetic",
            json={"count": 12, "seed": 3, "clustered": False},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["points"]), 12)
        self.assertEqual(payload["source"], "synthetic")

    def test_closest_pair_endpoint(self) -> None:
        response = self.client.post(
            "/api/closest-pair",
            json={
                "points": [
                    {"id": "a", "lat": 24.8607, "lng": 67.0011},
                    {"id": "b", "lat": 24.8608, "lng": 67.0012},
                    {"id": "c", "lat": 24.8700, "lng": 67.0100},
                ],
                "algorithms": ["brute_force", "divide_conquer"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["agree"])
        self.assertEqual(len(payload["results"]), 2)
        self.assertGreater(payload["results"][0]["distance_m"], 0)

    def test_route_endpoint_straight_line(self) -> None:
        response = self.client.post(
            "/api/route/optimize",
            json={
                "locations": [
                    {"id": "depot", "lat": 24.86, "lng": 67.00},
                    {"id": "a", "lat": 24.861, "lng": 67.001},
                    {"id": "b", "lat": 24.862, "lng": 67.002},
                    {"id": "c", "lat": 24.863, "lng": 67.003},
                ],
                "metric": "straight_line",
                "algorithms": ["exact", "nearest_neighbor", "two_opt"],
                "include_geometry": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["unit"], "m")
        self.assertIn("straight segments", payload["geometry_source"] or "")
        self.assertEqual(len(payload["results"]), 3)
        exact = next(item for item in payload["results"] if item["algorithm"] == "exact")
        nearest = next(
            item for item in payload["results"] if item["algorithm"] == "nearest_neighbor"
        )
        self.assertGreaterEqual(nearest["cost"], exact["cost"])

    def test_route_endpoint_rejects_asymmetric_matrix(self) -> None:
        matrix = [
            [0, 1, 2],
            [3, 0, 1],
            [2, 1, 0],
        ]
        response = self.client.post(
            "/api/route/optimize",
            json={
                "locations": [
                    {"lat": 24.86, "lng": 67.0},
                    {"lat": 24.87, "lng": 67.0},
                    {"lat": 24.88, "lng": 67.0},
                ],
                "metric": "precomputed",
                "matrix": matrix,
                "algorithms": ["nearest_neighbor"],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_benchmarks_and_report(self) -> None:
        closest = self.client.post(
            "/api/benchmarks/closest-pair",
            json={"sizes": [10, 20], "repetitions": 1, "seed": 1},
        )
        self.assertEqual(closest.status_code, 200)
        self.assertEqual(len(closest.json()["series"]), 4)

        route = self.client.post(
            "/api/benchmarks/route",
            json={
                "sizes": [5, 8],
                "repetitions": 1,
                "seed": 1,
                "algorithms": ["exact", "nearest_neighbor", "two_opt"],
            },
        )
        self.assertEqual(route.status_code, 200)
        self.assertTrue(route.json()["series"])

        report = self.client.post(
            "/api/reports/export",
            json={
                "title": "GeoRoute Test",
                "format": "csv",
                "payload": closest.json(),
            },
        )
        self.assertEqual(report.status_code, 200)
        self.assertIn("input_size", report.text)


if __name__ == "__main__":
    unittest.main()
