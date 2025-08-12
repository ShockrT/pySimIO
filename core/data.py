from dataclasses import dataclass, field
from typing import List

@dataclass
class Pump:
    name: str
    plc_tag: str
    max_flow: float
    control_variable: str
    fidelity: str = "Simple"  # Optional, for simulation mode

@dataclass
class ControlValve:
    plc_tag: str
    name: str
    cv: float
    open_pct: float = 100.0
    fidelity: str = "Simple"

@dataclass
class ControlVariable:
    plc_tag: str
    name: str = ""
    gain: float = 1.0
    EUMin: float = 0.0
    EUMax: float = 100.0
    value: float = 0.0

    def serialize_cv(self):
        return {
            "name": self.name,
            "EU Min": self.EUMin,
            "EU Max": self.EUMax,
            "gain": self.gain,
        }

@dataclass
class Valve:
    plc_tag: str
    name: str = ""
    tag: str = ""
    is_open: bool = False

@dataclass
class FlowPath:
    name: str = ""
    description: str = ""
    segments: List[Valve] = field(default_factory=list)

    def serialize_fp(self):
        return {
            "description": self.description,
            "segments": [v.name for v in self.segments]
        }

@dataclass
class AnalogSensor:
    plc_tag_value: str
    plc_tag_min: str
    plc_tag_max: str
    name: str = ""
    value: float = 0.0
    eu_min: float = 0.0
    eu_max: float = 0.0
    sim_rate: float = 1.0
    model_type: str = ""
    model_configured: bool = False
    active: bool = False
    cv: List[ControlVariable] = field(default_factory=list)
    cv_relationship: List[str] = field(default_factory=list)

    def toggle_active(self):
        self.active = not self.active

    def serialize_pv(self):
        return {
            "name": self.name,
            "value": self.value,
            "model_type": self.model_type,
            "cv": [vars(cv) for cv in self.cv]
        }

class PLCData:
    def __init__(self):
        self.pax_modules_list = [] # All PlantPAx modules found in tag export
        self.pv_list = [] # List of process variables in the PLC (type: ProcessVariable)
        self.cv_list = [] # List of CV Names (strings)
        self.valve_list = []
        self.flow_paths = []
        # module_dict is a dictionary whose keys are the PlantPAx module types
        # and whose values are lists of PlantPAx modules (represented as dictionaries) with that data type
        self.module_dict = {}

    def print_tags(self):
        for pv in self.pv_list:
            print(pv.name)

@dataclass
class PlantPaxModule:
    name: str
    data_type: str
    path: str
    module_type: str  # e.g., 'Pump', 'ControlValve', 'AnalogInput', 'DiscreteValve'
