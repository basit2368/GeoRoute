from __future__ import annotations

import threading
import uuid

from .models import Bounds, DatasetOut, PointOut


class DatasetStore:
    """Small in-memory dataset registry for a demo deployment."""

    def __init__(self) -> None:
        self._items: dict[str, DatasetOut] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        points: list[PointOut],
        name: str,
        source: str,
        seed: int | None = None,
        bounds: Bounds | None = None,
    ) -> DatasetOut:
        dataset = DatasetOut(
            id=uuid.uuid4().hex[:12],
            name=name,
            source=source,
            seed=seed,
            bounds=bounds,
            points=points,
        )
        with self._lock:
            self._items[dataset.id] = dataset
        return dataset

    def get(self, dataset_id: str) -> DatasetOut | None:
        with self._lock:
            return self._items.get(dataset_id)

    def list(self) -> list[DatasetOut]:
        with self._lock:
            return list(self._items.values())

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            return self._items.pop(dataset_id, None) is not None


dataset_store = DatasetStore()
