from dataclasses import dataclass, field
from typing import Dict
from core.data import ProcessVariable, FlowPath

@dataclass
class PVModel:
    model_id: int = -1
    flow_path: FlowPath = field(default_factory=FlowPath)
    conditions: Dict[str, bool] = field(default_factory=lambda: {"has cv": False})
    is_configured: bool = False

    def check_config(self, pv: ProcessVariable):
        if len(pv.cv) == 0:
            self.conditions["has cv"] = False
        else:
            self.conditions["has cv"] = True
        self.is_configured = all(self.conditions.values())

@dataclass
class Flow(PVModel):
    model_id: int = 1

    def __post_init__(self):
        super().check_config = self.check_config  # inherit config logic

@dataclass
class Pressure(PVModel):
    model_id: int = 2

    def __post_init__(self):
        super().check_config = self.check_config # inherit config logic


class Temperature(PVModel):
    model_id = 3

    def __post_init__(self):
        super().check_config = self.check_config # inherit config logic
        self.conditions = {
            "has cv": False,
            "heat path open": False,
            "cool path open": False,
        }
        self.heat_path = FlowPath
        self.cool_path = FlowPath
        self.heat_rate = 0.0
        self.cool_rate = 0.0

class Level(PVModel):
    model_id = 4

    def __post_init__(self):
        super().check_config = self.check_config # inherit config logic
        self.conditions = {
            "has inlet path": False,
            "has outlet path": False,
        }
        self.inlet_paths = [FlowPath]
        self.outlet_paths = [FlowPath]
        self.inlet_flows = [0.0]
        self.outlet_flows = [0.0]