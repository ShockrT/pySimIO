"""Safe, optional bridge from simulated values to PLC tags."""

from __future__ import annotations

import logging
from typing import Callable


logger = logging.getLogger(__name__)
WriteValue = Callable[[str, float], bool | None]


class PlcSimBridge:
    """Write registered simulation values only when a PLC writer is available."""

    def __init__(self, write_fn: WriteValue | None = None) -> None:
        self._write_fn = write_fn
        self._sources: dict[str, Callable[[], float]] = {}
        self._running = False

    @property
    def is_available(self) -> bool:
        return callable(self._write_fn)

    def set_write_fn(self, write_fn: WriteValue | None) -> None:
        self._write_fn = write_fn

    def register_source(self, tag: str, getter: Callable[[], float]) -> None:
        normalized = tag.strip()
        if normalized:
            self._sources[normalized] = getter

    def clear_sources(self) -> None:
        self._sources.clear()

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def tick(self) -> dict[str, bool]:
        """Write one batch and return per-tag success without raising into the runtime."""
        results: dict[str, bool] = {}
        if not self._running or not self.is_available:
            return results

        assert self._write_fn is not None
        for tag, getter in tuple(self._sources.items()):
            try:
                value = float(getter())
                results[tag] = bool(self._write_fn(tag, value))
            except Exception:
                logger.exception("PLC bridge write failed for %s", tag)
                results[tag] = False
        return results


def validate_plc_tags(plc, tags: list[str]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for tag in tags:
        try:
            if callable(getattr(plc, "get_metadata", None)):
                plc.get_metadata(tag)
                results[tag] = True
            elif callable(getattr(plc, "read_tag", None)):
                results[tag] = plc.read_tag(tag) is not None
            else:
                results[tag] = False
        except Exception:
            results[tag] = False
    return results
