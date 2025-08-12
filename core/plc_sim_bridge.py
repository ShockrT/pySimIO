"""
plc_sim_bridge.py
Milestones 1–3: minimal, stable PLC bridge.

Public surface:
  - PlcSimBridge(write_fn)
      .register_source(tag: str, getter: () -> float)
      .start()
      .stop()
      .tick()        # call this on your scheduler cadence

Optional helper:
  - validate_plc_tags(plc, tags) -> dict[str, bool]
"""

from __future__ import annotations

from typing import Callable, Dict, List
import logging


logger = logging.getLogger("PLCBridge")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s'))
    logger.addHandler(_h)


class PlcSimBridge:
    """
    Bridges simulated PV values to PLC tags.

    Typical usage:
        bridge = PlcSimBridge(write_fn=plc.write_tag)
        bridge.register_source("MyTag", some_component.current_value)
        bridge.start()
        # On a fixed cadence:
        #   component.update(dt)
        #   bridge.tick()
    """
    def __init__(self, write_fn: Callable[[str, float], bool | None]):
        self._write_fn = write_fn
        self._sources: Dict[str, Callable[[], float]] = {}
        self._running: bool = False

    def register_source(self, tag: str, getter: Callable[[], float]) -> None:
        self._sources[tag] = getter

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def tick(self) -> None:
        if not self._running:
            return
        for tag, getter in list(self._sources.items()):
            try:
                value = float(getter())
            except Exception:
                continue  # bad getter shouldn't crash the loop
            try:
                self._write_fn(tag, value)
            except Exception:
                # Let PLC layer handle logging/backoff; don't crash core loop
                pass


def validate_plc_tags(plc, tags: List[str]) -> Dict[str, bool]:
    """
    Quick existence check for tags. Uses plc.get_metadata or a safe read if available.
    """
    results: Dict[str, bool] = {}
    for tag in tags:
        ok = True
        try:
            if hasattr(plc, "get_metadata"):
                _ = plc.get_metadata(tag)
            elif hasattr(plc, "read_tag"):
                _ = plc.read_tag(tag)
            else:
                ok = False
        except Exception:
            ok = False
        results[tag] = ok
    return results

def build_input_signals_from_plc(plc, components: list[object]) -> dict[str, dict]:
    inputs: dict[str, dict] = {}
    for comp in components:
        tag = getattr(comp, "plc_tag", None)
        if not tag:
            inputs[getattr(comp, "name", "PV")] = {}
            continue
        try:
            v = plc.read_tag(tag)
        except Exception:
            v = 0.0
        name = getattr(comp, "name", tag)
        # Heuristic mapping
        if hasattr(comp, "set_input"):
            inputs[name] = {"u": float(v)}
        elif hasattr(comp, "set_flows"):
            inputs[name] = {"qin": float(v), "qout": 0.0}
        else:
            inputs[name] = {"value": float(v)}
    return inputs