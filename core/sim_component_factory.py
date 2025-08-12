"""
sim_component_factory.py
Single public entrypoint to build SimComponents from ConfiguredModel.

Wiring notes (Milestone 2):
- The factory constructs each component with its numeric params.
- Orchestrator (below) wires cross-inputs (e.g., set_flows for Pressure/Level).
"""

from __future__ import annotations

from core.models import ConfiguredModel
from core.simulator import (
    SimComponent,
    Sensor,
    FlowComponent,
    PressureComponent,
    LevelComponent,
    TemperatureComponent,
)


def build_sim_component(obj: ConfiguredModel) -> SimComponent:
    """
    Create and return the appropriate simulation component for the given model.
    This only constructs the component; it does NOT wire cross-inputs.
    """
    if not hasattr(obj, "type"):
        raise TypeError("ConfiguredModel missing 'type'")

    t = (obj.type or "").strip().lower()
    p = obj.params or {}
    name = obj.name or "PV"

    if t == "sensor":
        return Sensor(
            name=name,
            source_component=None,
            attribute=None,
            noise_std=float(p.get("noise_std", 0.0)),
            lag_samples=int(p.get("lag_samples", 0)),
            initial=float(p.get("initial", 0.0)),
        )

    if t == "flow":
        return FlowComponent(
            name=name,
            k=float(p.get("k", 1.0)),
            tau=float(p.get("tau", 1.0)),
            initial=float(p.get("initial", 0.0)),
        )

    if t == "pressure":
        return PressureComponent(
            name=name,
            k_in=float(p.get("k_in", 1.0)),
            k_out=float(p.get("k_out", 1.0)),
            tau=float(p.get("tau", 2.0)),
            leak=float(p.get("leak", 0.0)),
            initial=float(p.get("initial", 0.0)),
        )

    if t == "level":
        return LevelComponent(
            name=name,
            area=float(p.get("area", 1.0)),
            initial=float(p.get("initial", 0.0)),
        )

    if t == "temperature":
        return TemperatureComponent(
            name=name,
            tau=float(p.get("tau", 5.0)),
            ambient=float(p.get("ambient", 25.0)),
            k=float(p.get("k", 1.0)),
            initial=p.get("initial"),  # None -> ambient
        )

    raise TypeError(f"Unsupported model type: {obj.type}")

def build_sim_components_from_models(models: list[ConfiguredModel]) -> list[SimComponent]:
    return [build_sim_component(m) for m in models]