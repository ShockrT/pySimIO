"""
models.py
Unified configuration contract for simulator components.

A ConfiguredModel corresponds to one simulated PV/output (e.g., a flow PV, a pressure PV).
- `type` controls which component the factory builds.
- `params` holds numeric config (tau, k, etc.).
- `inputs` is used to link cross-signals (e.g., inlet/outlet flow paths for pressure/level).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# Include "None" so the UI can safely initialize a new/empty model.
ModelType = Literal["None", "Flow", "Pressure", "Level", "Temperature", "Sensor"]


@dataclass
class ConfiguredModel:
    # Display/PV metadata
    name: str = ""                   # PV name / sensor name
    # NOTE: `type` remains the persisted/source-of-truth field.
    type: ModelType = "None"         # "None" | "Flow" | "Pressure" | "Level" | "Temperature" | "Sensor"
    tag: str = ""                    # PLC tag to write the simulated value to
    active: bool = True
    fidelity: int | str = 0          # reserved for future; not used directly here

    # Cross-wiring / upstream references (e.g., PV names/flow paths)
    # examples:
    #   Pressure:  {"inlet_flow": "FlowInPV", "outlet_flow": "FlowOutPV"}
    #   Level:     {"inlet_flow": "FillFlowPV", "outlet_flow": "DrainFlowPV"}
    #   Flow:      {"control": "PUMP-01"}  (optional)
    inputs: dict[str, str] = field(default_factory=dict)

    # Numeric parameters specific to the model type.
    #   Flow:        {"k":1.0, "tau":1.0, "initial":0.0}
    #   Pressure:    {"k_in":1.0, "k_out":1.0, "tau":2.0, "leak":0.0, "initial":0.0}
    #   Level:       {"area":1.0, "initial":0.0}
    #   Temperature: {"tau":5.0, "ambient":25.0, "k":1.0, "initial":25.0}
    params: dict[str, float] = field(default_factory=dict)

    # ---- Compatibility shim for UI code that expects `model_type` ----
    @property
    def model_type(self) -> ModelType:
        """Compatibility alias for `type` used by some UI code."""
        return self.type

    @model_type.setter
    def model_type(self, value: ModelType) -> None:
        self.type = value

    # ---- Helpers for safe (de)serialization ----
    @staticmethod
    def from_dict(data: dict) -> "ConfiguredModel":
        """
        Build a ConfiguredModel from a dict, accepting either 'type' or legacy 'model_type'.
        Missing keys are defaulted to safe values.
        """
        mtype: ModelType = data.get("type", data.get("model_type", "None"))
        return ConfiguredModel(
            name=data.get("name", ""),
            type=mtype,  # source of truth
            tag=data.get("tag", ""),
            active=data.get("active", True),
            fidelity=data.get("fidelity", 0),
            inputs=data.get("inputs", {}) or {},
            params=data.get("params", {}) or {},
        )

    def to_dict(self) -> dict:
        """
        Serialize using `type` as the canonical field. We also include `model_type`
        for forward compatibility with any UI expecting it.
        """
        return {
            "name": self.name,
            "type": self.type,
            "model_type": self.type,  # convenience for UI code
            "tag": self.tag,
            "active": self.active,
            "fidelity": self.fidelity,
            "inputs": dict(self.inputs),
            "params": dict(self.params),
        }
