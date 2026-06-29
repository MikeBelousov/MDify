from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any


class OCRModelRegistry:
    def __init__(
        self,
        *,
        detector_factory: Callable[[], Any],
        eslav_factory: Callable[[], Any],
        latin_factory: Callable[[], Any],
    ) -> None:
        self._factories = {
            "detector": detector_factory,
            "eslav": eslav_factory,
            "latin": latin_factory,
        }
        self._instances: dict[str, Any] = {}
        self._lock = RLock()

    def detector(self) -> Any:
        return self._get("detector")

    def eslav(self) -> Any:
        return self._get("eslav")

    def latin(self) -> Any:
        return self._get("latin")

    def _get(self, name: str) -> Any:
        with self._lock:
            if name not in self._instances:
                self._instances[name] = self._factories[name]()
            return self._instances[name]
