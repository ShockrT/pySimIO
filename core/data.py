from dataclasses import dataclass, field
from typing import List
from core.constants import PLANT_PAX_MODULES, PV_MODULE_TYPES, CV_MODULE_TYPES, VALVE_TYPES

@dataclass
class ControlVariable:
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
class ProcessVariable:
    name: str = ""
    value: float = 0.0
    eu_min: float = 0.0
    eu_max: float = 0.0
    sim_rate: float = 1.0
    model: str = ""
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
            "model": self.model,
            "model_type": self.model_type,
            "cv": [vars(cv) for cv in self.cv]
        }

    #def check_model(self, device_type: str) -> bool:
    #     if device_type in MODEL_TYPES:
    #         match device_type:
    #             case "flow":
    #                 pass

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

    def get_plant_pax_modules(self, input_data):
        # Get list of all controller-scoped PlantPAx module tags from the input data
        all_pax_tags_list = [item for item in input_data
                           if item["DATATYPE"] in PLANT_PAX_MODULES and str(item["SCOPE"]) == "nan"]
        # Create new dictionary for each PlantPAx module tag
        for tag in all_pax_tags_list:
            new_module = {"Name": str(tag["NAME"]),
                          "Description": str(tag["DESCRIPTION"]),
                          "Data Type": str(tag["DATATYPE"])}
            # Add the new module to the PlantPAx module dictionary
            try:
                self.module_dict[new_module["Data Type"]].append(new_module)
            except KeyError:
                self.module_dict[new_module["Data Type"]] = [new_module]
            # Create new Process Variable object and add to list of Process Variables
            if new_module["Data Type"] in PV_MODULE_TYPES:
                new_pv = ProcessVariable()
                new_pv.name = new_module["Name"]
                self.pv_list.append(new_pv)
            # Populate a list of possible control variables based on data type
            if new_module["Data Type"] in CV_MODULE_TYPES:
                new_cv = ControlVariable()
                new_cv.name = new_module["Name"]
                self.cv_list.append(new_cv)
            # Populate a list of valves based on data type
            if new_module["Data Type"] in VALVE_TYPES:
                new_valve = Valve()
                new_valve.name = new_module["Name"]
                self.valve_list.append(new_valve)



