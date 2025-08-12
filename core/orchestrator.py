"""
orchestrator.py
Milestone 3–5 glue:
- Builds components from ConfiguredModels
- Wires cross-dependencies (Pressure/Level pull flows from Flow components)
- Registers PLC tag writers for ACTIVE models only
- Provides start/stop/step(dt) and a simple run_loop()
- Includes a merge helper for M5 "Read from PLC" button behavior
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

from models import ConfiguredModel
from simulator import SimComponent, Sensor, FlowComponent, PressureComponent, LevelComponent, TemperatureComponent
from sim_component_factory import build_sim_component
from plc_sim_bridge import PlcSimBridge


class SimulationOrchestrator:
    def __init__(self, models: List[ConfiguredModel], write_fn, dt: float = 0.2):
        self._models = models
        self._dt = float(dt)
        self._components: Dict[str, SimComponent] = {}
        self._bridge = PlcSimBridge(write_fn=write_fn)
        self._running = False

        # Cross-wiring cache: comp name -> (qin_from, qout_from) comp names
        self._pressure_links: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
        self._level_links: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    # ---------- build & wire ----------

    def build(self) -> None:
        """Build components from configs and prepare PLC mapping for active ones."""
        # Build all components
        for cm in self._models:
            comp = build_sim_component(cm)
            self._components[cm.name] = comp

        # Wire cross inputs (by names in inputs dict)
        for cm in self._models:
            t = cm.type.lower()
            comp = self._components[cm.name]

            if t == "pressure":
                inlet_name = cm.inputs.get("inlet_flow")
                outlet_name = cm.inputs.get("outlet_flow")
                self._pressure_links[cm.name] = (inlet_name, outlet_name)

            elif t == "level":
                inlet_name = cm.inputs.get("inlet_flow")
                outlet_name = cm.inputs.get("outlet_flow")
                self._level_links[cm.name] = (inlet_name, outlet_name)

            elif t == "sensor":
                # If the sensor is meant to mirror another PV:
                src = cm.inputs.get("source_component")
                attr = cm.inputs.get("attribute")
                if src and attr and isinstance(comp, Sensor) and src in self._components:
                    comp._src = self._components[src]
                    comp._attr = attr

        # Register PLC write sources for ACTIVE models only
        for cm in self._models:
            if not cm.active:
                continue
            comp = self._components[cm.name]
            if cm.tag:
                self._bridge.register_source(cm.tag, comp.current_value)

    # ---------- run control ----------

    def start(self) -> None:
        self._running = True
        self._bridge.start()

    def stop(self) -> None:
        self._running = False
        self._bridge.stop()

    def step(self, dt: Optional[float] = None) -> None:
        """Advance all components by one time step and write to PLC (active only)."""
        if not self._running:
            return
        h = float(dt if dt is not None else self._dt)

        # Wire flows dynamically for pressure/level each tick
        for name, comp in self._components.items():
            if isinstance(comp, PressureComponent):
                inlet_name, outlet_name = self._pressure_links.get(name, (None, None))
                qin = self._components[inlet_name].current_value() if inlet_name and inlet_name in self._components else 0.0
                qout = self._components[outlet_name].current_value() if outlet_name and outlet_name in self._components else 0.0
                comp.set_flows(qin, qout)

            elif isinstance(comp, LevelComponent):
                inlet_name, outlet_name = self._level_links.get(name, (None, None))
                qin = self._components[inlet_name].current_value() if inlet_name and inlet_name in self._components else 0.0
                qout = self._components[outlet_name].current_value() if outlet_name and outlet_name in self._components else 0.0
                comp.set_flows(qin, qout)

        # Update components
        for comp in self._components.values():
            comp.update(h)

        # Write active PVs to PLC
        self._bridge.tick()

    def run_loop(self, duration_sec: Optional[float] = None) -> None:
        """
        Simple loop (blocking). GUI should prefer a QTimer / thread approach, but this is handy for tests.
        """
        self.start()
        try:
            t0 = time.time()
            while self._running:
                self.step(self._dt)
                time.sleep(self._dt)
                if duration_sec is not None and (time.time() - t0) >= duration_sec:
                    break
        finally:
            self.stop()

    # ---------- utility for M5 "Read from PLC" merge ----------

    @staticmethod
    def merge_discovered_pvs(existing: List[ConfiguredModel], discovered: List[ConfiguredModel]) -> tuple[List[ConfiguredModel], dict]:
        """
        Merge discovered PLC PVs into existing configs WITHOUT overwriting existing entries.
        Uses (tag) as the unique key. Returns (new_list, stats).
        """
        by_tag = {cm.tag: cm for cm in existing if cm.tag}
        added = 0
        skipped = 0
        for cm in discovered:
            if not cm.tag or cm.tag in by_tag:
                skipped += 1
                continue
            by_tag[cm.tag] = cm
            added += 1
        merged = list(by_tag.values())
        stats = {"added": added, "skipped": skipped, "updated": 0}
        return merged, stats

    # ---------- accessors ----------

    @property
    def components(self) -> Dict[str, SimComponent]:
        return self._components.copy()
